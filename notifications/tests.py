import io
import sys
from contextlib import redirect_stdout
from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.text import slugify

from notifications.models import Tag, Post, DeletedPost


class Phase1ModelsTestCase(TestCase):
    def test_tag_creation_and_str(self):
        tag = Tag.objects.create(name="django")
        self.assertEqual(str(tag), "django")
        self.assertEqual(Tag.objects.count(), 1)

    def test_post_creation_and_str(self):
        post = Post.objects.create(
            title="Introduction to Django Models",
            slug="intro-to-django-models",
            content="Testing model fields"
        )
        self.assertEqual(str(post), "Introduction to Django Models")
        self.assertEqual(post.slug, "intro-to-django-models")

    def test_post_tag_m2m_relationship(self):
        post = Post.objects.create(title="Post with Tags", slug="post-with-tags")
        tag1 = Tag.objects.create(name="python")
        tag2 = Tag.objects.create(name="framework")

        post.tags.add(tag1, tag2)
        self.assertEqual(post.tags.count(), 2)
        self.assertIn(tag1, post.tags.all())
        self.assertIn(tag2, post.tags.all())

    def test_deleted_post_creation_and_str(self):
        deleted = DeletedPost.objects.create(
            original_post_id=42,
            title="Old Post Title",
            slug="old-post-title",
            content="Archived text"
        )
        self.assertEqual(str(deleted), "Deleted: Old Post Title (Original ID: 42)")
        self.assertEqual(deleted.original_post_id, 42)


class Phase2SignalSetupTestCase(TestCase):
    def test_notifications_config_is_loaded(self):
        app_config = apps.get_app_config('notifications')
        self.assertEqual(app_config.name, 'notifications')

    def test_signals_module_imported_on_ready(self):
        import notifications.signals
        self.assertIn('notifications.signals', sys.modules)
        self.assertTrue(getattr(notifications.signals, 'SIGNALS_LOADED', False))


class Phase3PreSaveSignalTestCase(TestCase):
    def test_pre_save_auto_generates_slug_when_empty(self):
        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            post = Post.objects.create(
                title="Mastering Django Signals In Depth",
                content="Testing pre_save auto slug creation."
            )
        self.assertEqual(post.slug, "mastering-django-signals-in-depth")
        self.assertIn("[PRE-SAVE] Auto-generated slug", stdout_capture.getvalue())

    def test_pre_save_preserves_custom_slug(self):
        post = Post.objects.create(
            title="Post With Explicit Slug",
            slug="my-custom-slug",
            content="Custom slug should not be overwritten."
        )
        self.assertEqual(post.slug, "my-custom-slug")

    def test_pre_save_regenerates_slug_if_cleared_on_update(self):
        post = Post.objects.create(
            title="Initial Title",
            slug="initial-slug"
        )
        self.assertEqual(post.slug, "initial-slug")

        post.slug = ""
        post.title = "Updated New Title"
        post.save()
        self.assertEqual(post.slug, slugify("Updated New Title"))


class Phase4PostSaveSignalTestCase(TestCase):
    def test_post_save_user_welcome_email_on_creation(self):
        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            user = User.objects.create_user(
                username="new_intern",
                email="intern@example.com",
                password="Password123!"
            )

        output = stdout_capture.getvalue()
        self.assertIn("[POST-SAVE] New user created", output)
        self.assertIn("[EMAIL NOTIFICATION] Welcome email sent to: intern@example.com", output)

    def test_post_save_user_no_welcome_email_on_update(self):
        user = User.objects.create_user(
            username="existing_intern",
            email="existing@example.com",
            password="Password123!"
        )

        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            user.first_name = "InternName"
            user.save()

        output = stdout_capture.getvalue()
        self.assertNotIn("[EMAIL NOTIFICATION]", output)


class Phase5DeleteSignalsTestCase(TestCase):
    def test_pre_delete_creates_backup_record(self):
        post = Post.objects.create(
            title="Post to Archive Before Deletion",
            content="Archival payload content."
        )
        post_id = post.pk
        post_title = post.title
        post_slug = post.slug

        self.assertEqual(DeletedPost.objects.filter(original_post_id=post_id).count(), 0)

        stdout_capture = io.StringIO()
        with redirect_stdout(stdout_capture):
            post.delete()

        output = stdout_capture.getvalue()
        self.assertIn("[PRE-DELETE BACKUP]", output)
        self.assertIn("[POST-DELETE]", output)

        self.assertFalse(Post.objects.filter(pk=post_id).exists())

        backup = DeletedPost.objects.filter(original_post_id=post_id).first()
        self.assertIsNotNone(backup)
        self.assertEqual(backup.title, post_title)
        self.assertEqual(backup.slug, post_slug)
        self.assertEqual(backup.content, "Archival payload content.")
        self.assertIsNotNone(backup.deleted_at)


class Phase6M2MSignalTestCase(TestCase):
    def setUp(self):
        self.tag_django = Tag.objects.create(name="django")
        self.tag_signals = Tag.objects.create(name="signals")

    def test_m2m_changed_pre_add_and_post_remove(self):
        post = Post.objects.create(title="Post For M2M Testing")

        stdout_capture_add = io.StringIO()
        with redirect_stdout(stdout_capture_add):
            post.tags.add(self.tag_django, self.tag_signals)

        output_add = stdout_capture_add.getvalue()
        self.assertIn("Action: 'pre_add'", output_add)
        self.assertIn(f"ID: {post.pk}", output_add)
        self.assertIn(f"Affected Tag PKs: {[self.tag_django.pk, self.tag_signals.pk]}", output_add)

        stdout_capture_remove = io.StringIO()
        with redirect_stdout(stdout_capture_remove):
            post.tags.remove(self.tag_signals)

        output_remove = stdout_capture_remove.getvalue()
        self.assertIn("Action: 'post_remove'", output_remove)
        self.assertIn(f"ID: {post.pk}", output_remove)
        self.assertIn(f"Affected Tag PKs: [{self.tag_signals.pk}]", output_remove)
