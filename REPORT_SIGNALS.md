# Django Signals Report (REPORT_SIGNALS.md)

This report details the implementation of Django signal handlers for model lifecycle events in the `notifications` application. It covers signal registration methods, argument usage, recursion prevention techniques, and execution traces with underlying SQL queries.

---

## 1. Architecture and Setup

### App Registration and Lifecycle (`notifications/apps.py`)
To prevent missed signals or premature imports during startup, signal receivers are imported inside the `ready()` method of `NotificationsConfig`:

```python
from django.apps import AppConfig

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        import notifications.signals
```

The app is registered in `config/settings.py` via `'notifications.apps.NotificationsConfig'`.

### Models (`notifications/models.py`)
- **`Tag`**: Category labels for posts (`name`).
- **`Post`**: Main model with `title`, `slug`, `content`, `tags` (`ManyToManyField`), `created_at`, and `updated_at`.
- **`DeletedPost`**: Backup model containing `original_post_id`, `title`, `slug`, `content`, and `deleted_at`.

---

## 2. Signal Receivers Breakdown

### A. Automatic Slug Generation (`pre_save`)

- **Signal**: `django.db.models.signals.pre_save`
- **Sender**: `notifications.models.Post`
- **Registration**: `@receiver(pre_save, sender=Post)`
- **Arguments Used**: `sender`, `instance`, `**kwargs`
- **Implementation**:
  ```python
  @receiver(pre_save, sender=Post)
  def auto_generate_slug_on_pre_save(sender, instance, **kwargs):
      if not instance.slug:
          instance.slug = slugify(instance.title)
          print(f"[PRE-SAVE] Auto-generated slug '{instance.slug}' for Post '{instance.title}'")
  ```
- **Recursion Prevention**:
  The receiver mutates `instance.slug` directly on the in-memory model instance. It **never calls `instance.save()`**. Because `pre_save` executes right before the SQL `INSERT` or `UPDATE` query is dispatched, any modification to attributes on `instance` is automatically written to the database in the pending query. Calling `instance.save()` inside this receiver would re-trigger `pre_save`, resulting in an infinite recursion loop and a `RecursionError`.

---

### B. User Welcome Notification (`post_save`)

- **Signal**: `django.db.models.signals.post_save`
- **Sender**: `django.contrib.auth.models.User`
- **Registration**: `@receiver(post_save, sender=User)`
- **Arguments Used**: `sender`, `instance`, `created`, `**kwargs`
- **Implementation**:
  ```python
  def send_welcome_email(user_email: str) -> None:
      msg = f"[EMAIL NOTIFICATION] Welcome email sent to: {user_email}"
      print(msg)
      logger.info(msg)

  @receiver(post_save, sender=User)
  def user_welcome_notification(sender, instance, created, **kwargs):
      if created:
          recipient = instance.email if instance.email else instance.username
          print(f"[POST-SAVE] New user created (ID: {instance.pk}, Username: '{instance.username}').")
          send_welcome_email(recipient)
  ```
- **Logic & Recursion Safety**:
  The `created` flag is a boolean supplied by Django indicating whether a new row was inserted (`True`) or an existing row was updated (`False`). Evaluating `if created:` ensures that welcome emails are only dispatched upon initial registration, not on subsequent profile updates or password changes. No `instance.save()` call is made within the handler.

---

### C. Pre-Deletion Backup (`pre_delete`)

- **Signal**: `django.db.models.signals.pre_delete`
- **Sender**: `notifications.models.Post`
- **Registration**: `@receiver(pre_delete, sender=Post)`
- **Arguments Used**: `sender`, `instance`, `**kwargs`
- **Implementation**:
  ```python
  @receiver(pre_delete, sender=Post)
  def backup_post_before_deletion(sender, instance, **kwargs):
      backup = DeletedPost.objects.create(
          original_post_id=instance.pk,
          title=instance.title,
          slug=instance.slug,
          content=instance.content,
          deleted_at=timezone.now(),
      )
      msg = f"[PRE-DELETE BACKUP] Archived Post '{instance.title}' (ID: {instance.pk}) into DeletedPost (Backup ID: {backup.pk})"
      print(msg)
      logger.info(msg)
  ```
- **Behavior**:
  Fires right before the database deletion query runs. The receiver copies `instance.pk` and field data into `DeletedPost`. It does not raise an exception or abort the transaction, allowing the actual `Post` row to be deleted immediately afterward.

---

### D. Post-Deletion Confirmation (`post_delete`) — Manual Connect

- **Signal**: `django.db.models.signals.post_delete`
- **Sender**: `notifications.models.Post`
- **Registration**: Explicit manual registration via `post_delete.connect()`
- **Arguments Used**: `sender`, `instance`, `**kwargs`
- **Implementation**:
  ```python
  def post_delete_post_handler(sender, instance, **kwargs):
      msg = f"[POST-DELETE] Post '{instance.title}' (ID: {instance.pk}) was deleted from database."
      print(msg)
      logger.info(msg)

  post_delete.connect(post_delete_post_handler, sender=Post, dispatch_uid="post_delete_post_manual")
  ```
- **Registration Distinction**:
  Demonstrates manual signal binding using `signal.connect()` with `dispatch_uid` rather than decorator syntax, fulfilling both connection patterns required by the assignment.

---

### E. Many-to-Many Change Tracking (`m2m_changed`)

- **Signal**: `django.db.models.signals.m2m_changed`
- **Sender**: `Post.tags.through` (intermediary through-table `notifications_post_tags`)
- **Registration**: `@receiver(m2m_changed, sender=Post.tags.through)`
- **Arguments Used**: `sender`, `instance`, `action`, `pk_set`, `**kwargs`
- **Implementation**:
  ```python
  @receiver(m2m_changed, sender=Post.tags.through)
  def track_post_tags_changes(sender, instance, action, pk_set, **kwargs):
      if action in ["pre_add", "post_remove"]:
          now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")
          pk_list = sorted(list(pk_set)) if pk_set else []
          log_msg = f"[{now_str}] [M2M TRACKING] Action: '{action}' | Instance: Post '{instance.title}' (ID: {instance.pk}) | Affected Tag PKs: {pk_list}"
          print(log_msg)
          logger.info(log_msg)
  ```
- **Arguments Detail**:
  - `action`: String identifying the event (`"pre_add"`, `"post_remove"`).
  - `instance`: The `Post` instance being modified.
  - `pk_set`: The Python `set` of primary keys of the `Tag` records being added or removed.
  - `django.utils.timezone.now()`: Timezone-aware UTC timestamp included in the log entry.

---

## 3. Signal Summary Matrix

| Signal | Sender | Trigger Event | Registration | Key Arguments | Recursion Prevention |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pre_save` | `Post` | Before SQL `INSERT`/`UPDATE` | `@receiver` | `sender`, `instance` | Mutate in-memory attributes; never call `save()` |
| `post_save` | `User` | After SQL `INSERT`/`UPDATE` | `@receiver` | `sender`, `instance`, `created` | Check `if created:`; do not call `save()` |
| `pre_delete` | `Post` | Before SQL `DELETE` | `@receiver` | `sender`, `instance` | Creates row in backup table; does not halt delete |
| `post_delete` | `Post` | After SQL `DELETE` | `manual connect()` | `sender`, `instance` | Read-only audit log; no save invoked |
| `m2m_changed` | `Post.tags.through` | On M2M relationship changes | `@receiver` | `instance`, `action`, `pk_set` | Filters on targeted actions (`pre_add`, `post_remove`) |

---

## 4. Verification and Sample Outputs

### Running Demonstration Command
```bash
python manage.py signals_demo
```

### Execution Trace & SQL Queries

```text
>>> STARTING DJANGO SIGNALS DEMONSTRATION <<<

================================================================================
  STEP 1: AUTOMATIC SLUG GENERATION (PRE_SAVE)
================================================================================
[PRE-SAVE] Auto-generated slug 'demo-post-mastering-django-signals-from-scratch' for Post 'Demo Post: Mastering Django Signals from Scratch'
Result -> ID: 3 | Title: 'Demo Post: Mastering Django Signals from Scratch' | Slug: 'demo-post-mastering-django-signals-from-scratch'

[SQL TRACE] Queries for 'Create Post with empty slug' (Count: 1):
  (1) [0.000s] INSERT INTO "notifications_post" ("title", "slug", "content", "created_at", "updated_at") VALUES ('Demo Post: Mastering Django Signals from Scratch', 'demo-post-mastering-django-signals-from-scratch', 'Signals allow decoupled applications to get notified of events.', '2026-10-29 14:53:47.967848', '2026-10-29 14:53:47.967858') RETURNING "notifications_post"."id"
Result -> ID: 4 | Title: 'Demo Post: Advanced Architectural Patterns' | Slug: 'my-custom-predefined-slug'

[SQL TRACE] Queries for 'Create Post with custom slug' (Count: 1):
  (1) [0.000s] INSERT INTO "notifications_post" ("title", "slug", "content", "created_at", "updated_at") VALUES ('Demo Post: Advanced Architectural Patterns', 'my-custom-predefined-slug', 'Custom slug test.', '2026-10-29 14:53:47.968228', '2026-10-29 14:53:47.968233') RETURNING "notifications_post"."id"
Result -> ID: 3 | Title: 'Demo Post: Mastering Django Signals from Scratch' | Slug: 'demo-post-mastering-django-signals-from-scratch'

[SQL TRACE] Queries for 'Update Post content' (Count: 1):
  (1) [0.000s] UPDATE "notifications_post" SET "title" = 'Demo Post: Mastering Django Signals from Scratch', "slug" = 'demo-post-mastering-django-signals-from-scratch', "content" = 'Updated content: Demonstrating that pre_save doesn''t alter existing slug.', "created_at" = '2026-10-29 14:53:47.967848', "updated_at" = '2026-10-29 14:53:47.968612' WHERE "notifications_post"."id" = 3
[PRE-SAVE] Auto-generated slug 'demo-post-mastering-django-signals-and-receivers' for Post 'Demo Post: Mastering Django Signals and Receivers'
Result -> ID: 3 | Title: 'Demo Post: Mastering Django Signals and Receivers' | Slug: 'demo-post-mastering-django-signals-and-receivers'

[SQL TRACE] Queries for 'Regenerate slug on Post' (Count: 1):
  (1) [0.000s] UPDATE "notifications_post" SET "title" = 'Demo Post: Mastering Django Signals and Receivers', "slug" = 'demo-post-mastering-django-signals-and-receivers', "content" = 'Updated content: Demonstrating that pre_save doesn''t alter existing slug.', "created_at" = '2026-10-29 14:53:47.967848', "updated_at" = '2026-10-29 14:53:47.969044' WHERE "notifications_post"."id" = 3

================================================================================
  STEP 2: USER WELCOME NOTIFICATION (POST_SAVE)
================================================================================
[POST-SAVE] New user created (ID: 2, Username: 'demo_user_signals').
[EMAIL NOTIFICATION] Welcome email sent to: demouser@example.com
User Record Created -> ID: 2 | Username: demo_user_signals | Email: demouser@example.com

[SQL TRACE] Queries for 'Create new User' (Count: 1):
  (1) [0.000s] INSERT INTO "auth_user" ("password", "last_login", "is_superuser", "username", "first_name", "last_name", "email", "is_staff", "is_active", "date_joined") VALUES ('pbkdf2_sha256$1500000$dMaYGM35fBayC9AX6Tk94N$FoYX2bdfAHsVDsNoQQSdqW6AU8vuRLj6wsoxZQSMRE8=', NULL, 0, 'demo_user_signals', '', '', 'demouser@example.com', 0, 1, '2026-10-29 14:53:47.969393') RETURNING "auth_user"."id"
User Updated -> First Name: Alex

[SQL TRACE] Queries for 'Update existing User' (Count: 1):
  (1) [0.000s] UPDATE "auth_user" SET "password" = 'pbkdf2_sha256$1500000$dMaYGM35fBayC9AX6Tk94N$FoYX2bdfAHsVDsNoQQSdqW6AU8vuRLj6wsoxZQSMRE8=', "last_login" = NULL, "is_superuser" = 0, "username" = 'demo_user_signals', "first_name" = 'Alex', "last_name" = '', "email" = 'demouser@example.com', "is_staff" = 0, "is_active" = 1, "date_joined" = '2026-10-29 14:53:47.969393' WHERE "auth_user"."id" = 2

================================================================================
  STEP 3: MANY-TO-MANY CHANGE TRACKING (M2M_CHANGED)
================================================================================
[2026-10-29 14:53:48 UTC] [M2M TRACKING] Action: 'pre_add' | Instance: Post 'Demo Post: Mastering Django Signals and Receivers' (ID: 3) | Affected Tag PKs: [4, 5, 6]
Post Tags now: ['django', 'python', 'signals']

[SQL TRACE] Queries for 'Add tags to Post (m2m pre_add)' (Count: 5):
  (1) [0.000s] BEGIN
  (2) [0.000s] SELECT "notifications_post_tags"."tag_id" AS "tag" FROM "notifications_post_tags" WHERE ("notifications_post_tags"."post_id" = 3 AND "notifications_post_tags"."tag_id" IN (4, 5, 6))
  (3) [0.000s] INSERT OR IGNORE INTO "notifications_post_tags" ("post_id", "tag_id") VALUES (3, 4), (3, 5), (3, 6)
  (4) [0.000s] COMMIT
  (5) [0.000s] SELECT "notifications_tag"."id", "notifications_tag"."name" FROM "notifications_tag" INNER JOIN "notifications_post_tags" ON ("notifications_tag"."id" = "notifications_post_tags"."tag_id") WHERE "notifications_post_tags"."post_id" = 3 ORDER BY "notifications_tag"."name" ASC
[2026-10-29 14:53:48 UTC] [M2M TRACKING] Action: 'post_remove' | Instance: Post 'Demo Post: Mastering Django Signals and Receivers' (ID: 3) | Affected Tag PKs: [6]
Post Tags now: ['django', 'signals']

[SQL TRACE] Queries for 'Remove tag from Post (m2m post_remove)' (Count: 4):
  (1) [0.000s] BEGIN
  (2) [0.000s] DELETE FROM "notifications_post_tags" WHERE ("notifications_post_tags"."post_id" = 3 AND "notifications_post_tags"."tag_id" IN (6))
  (3) [0.000s] COMMIT
  (4) [0.000s] SELECT "notifications_tag"."id", "notifications_tag"."name" FROM "notifications_tag" INNER JOIN "notifications_post_tags" ON ("notifications_tag"."id" = "notifications_post_tags"."tag_id") WHERE "notifications_post_tags"."post_id" = 3 ORDER BY "notifications_tag"."name" ASC

================================================================================
  STEP 4: PRE-DELETION BACKUP & POST-DELETION (PRE_DELETE & POST_DELETE)
================================================================================
Deleting Post (ID: 3, Title: 'Demo Post: Mastering Django Signals and Receivers')...
[PRE-DELETE BACKUP] Archived Post 'Demo Post: Mastering Django Signals and Receivers' (ID: 3) into DeletedPost (Backup ID: 3)
[POST-DELETE] Post 'Demo Post: Mastering Django Signals and Receivers' (ID: 3) was deleted from database.

[SQL TRACE] Queries for 'Delete Post' (Count: 5):
  (1) [0.000s] BEGIN
  (2) [0.000s] INSERT INTO "notifications_deletedpost" ("original_post_id", "title", "slug", "content", "deleted_at") VALUES (3, 'Demo Post: Mastering Django Signals and Receivers', 'demo-post-mastering-django-signals-and-receivers', 'Updated content: Demonstrating that pre_save doesn''t alter existing slug.', '2026-10-29 14:53:48.085758') RETURNING "notifications_deletedpost"."id"
  (3) [0.000s] DELETE FROM "notifications_post_tags" WHERE "notifications_post_tags"."post_id" IN (3)
  (4) [0.000s] DELETE FROM "notifications_post" WHERE "notifications_post"."id" IN (3)
  (5) [0.000s] COMMIT
Original Post exists in Post table: False
Backup record in DeletedPost: ID=3, Original ID=3, Title='Demo Post: Mastering Django Signals and Receivers', Slug='demo-post-mastering-django-signals-and-receivers', Deleted At=2026-10-29 14:53:48.085758+00:00
[PRE-DELETE BACKUP] Archived Post 'Demo Post: Advanced Architectural Patterns' (ID: 4) into DeletedPost (Backup ID: 4)
[POST-DELETE] Post 'Demo Post: Advanced Architectural Patterns' (ID: 4) was deleted from database.

>>> ALL DEMONSTRATION STEPS COMPLETED SUCCESSFULLY <<<
```

---

### Running Automated Test Suite
```bash
python manage.py test
```
Result:
```text
Ran 13 tests in 0.228s
OK
```

