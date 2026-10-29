from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import connection, reset_queries

from notifications.models import Post, DeletedPost, Tag


class Command(BaseCommand):
    help = "Demonstrates all Django signals and executes SQL queries trace"

    def print_section(self, title: str):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"  {title.upper()}")
        self.stdout.write("=" * 80)

    def print_queries(self, step_title: str):
        queries = connection.queries
        query_count = len(queries)
        self.stdout.write(f"\n[SQL TRACE] Queries for '{step_title}' (Count: {query_count}):")
        if query_count == 0:
            self.stdout.write("  No SQL queries executed.")
        for idx, q in enumerate(queries, 1):
            cleaned_sql = " ".join(q["sql"].split())
            self.stdout.write(f"  ({idx}) [{q['time']}s] {cleaned_sql}")
        reset_queries()

    def handle(self, *args, **options):
        settings.DEBUG = True
        reset_queries()

        self.stdout.write(self.style.SUCCESS("\n>>> STARTING DJANGO SIGNALS DEMONSTRATION <<<\n"))

        Post.objects.filter(title__startswith="Demo Post").delete()
        DeletedPost.objects.filter(title__startswith="Demo Post").delete()
        User.objects.filter(username__startswith="demo_user").delete()
        Tag.objects.filter(name__in=["django", "signals", "python"]).delete()
        reset_queries()

        self.print_section("Step 1: Automatic Slug Generation (pre_save)")
        post1 = Post.objects.create(
            title="Demo Post: Mastering Django Signals from Scratch",
            content="Signals allow decoupled applications to get notified of events.",
            slug=""
        )
        self.stdout.write(f"Result -> ID: {post1.pk} | Title: '{post1.title}' | Slug: '{post1.slug}'")
        self.print_queries("Create Post with empty slug")

        post2 = Post.objects.create(
            title="Demo Post: Advanced Architectural Patterns",
            content="Custom slug test.",
            slug="my-custom-predefined-slug"
        )
        self.stdout.write(f"Result -> ID: {post2.pk} | Title: '{post2.title}' | Slug: '{post2.slug}'")
        self.print_queries("Create Post with custom slug")

        post1.content = "Updated content: Demonstrating that pre_save doesn't alter existing slug."
        post1.save()
        self.stdout.write(f"Result -> ID: {post1.pk} | Title: '{post1.title}' | Slug: '{post1.slug}'")
        self.print_queries("Update Post content")

        post1.slug = ""
        post1.title = "Demo Post: Mastering Django Signals and Receivers"
        post1.save()
        self.stdout.write(f"Result -> ID: {post1.pk} | Title: '{post1.title}' | Slug: '{post1.slug}'")
        self.print_queries("Regenerate slug on Post")

        self.print_section("Step 2: User Welcome Notification (post_save)")
        user1 = User.objects.create_user(
            username="demo_user_signals",
            email="demouser@example.com",
            password="SecureDemoPassword123!"
        )
        self.stdout.write(f"User Record Created -> ID: {user1.pk} | Username: {user1.username} | Email: {user1.email}")
        self.print_queries("Create new User")

        user1.first_name = "Alex"
        user1.save()
        self.stdout.write(f"User Updated -> First Name: {user1.first_name}")
        self.print_queries("Update existing User")

        self.print_section("Step 3: Many-to-Many Change Tracking (m2m_changed)")
        tag_django = Tag.objects.create(name="django")
        tag_signals = Tag.objects.create(name="signals")
        tag_python = Tag.objects.create(name="python")
        reset_queries()

        post1.tags.add(tag_django, tag_signals, tag_python)
        self.stdout.write(f"Post Tags now: {[t.name for t in post1.tags.all()]}")
        self.print_queries("Add tags to Post (m2m pre_add)")

        post1.tags.remove(tag_python)
        self.stdout.write(f"Post Tags now: {[t.name for t in post1.tags.all()]}")
        self.print_queries("Remove tag from Post (m2m post_remove)")

        self.print_section("Step 4: Pre-Deletion Backup & Post-Deletion (pre_delete & post_delete)")
        post_to_delete_id = post1.pk
        post_to_delete_title = post1.title

        self.stdout.write(f"Deleting Post (ID: {post_to_delete_id}, Title: '{post_to_delete_title}')...")
        post1.delete()
        self.print_queries("Delete Post")

        post_exists = Post.objects.filter(pk=post_to_delete_id).exists()
        backup_record = DeletedPost.objects.filter(original_post_id=post_to_delete_id).first()

        self.stdout.write(f"Original Post exists in Post table: {post_exists}")
        if backup_record:
            self.stdout.write(
                f"Backup record in DeletedPost: ID={backup_record.pk}, "
                f"Original ID={backup_record.original_post_id}, "
                f"Title='{backup_record.title}', Slug='{backup_record.slug}', "
                f"Deleted At={backup_record.deleted_at}"
            )

        post2.delete()
        reset_queries()

        self.stdout.write(self.style.SUCCESS("\n>>> ALL DEMONSTRATION STEPS COMPLETED SUCCESSFULLY <<<\n"))

