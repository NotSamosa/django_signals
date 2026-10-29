import io
import sys
from contextlib import redirect_stdout
from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.text import slugify

from notifications.models import Tag, Post, DeletedPost


class Phase1ModelsTestCase(TestCase):
    """
    Phase 1 unit tests: Validate Tag, Post, and DeletedPost models and relationships.
    """

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
    """
    Phase 2 unit tests: Validate signal module wiring and application ready() hook.
    """

    def test_notifications_config_is_loaded(self):
        app_config = apps.get_app_config('notifications')
        self.assertEqual(app_config.name, 'notifications')

    def test_signals_module_imported_on_ready(self):
        import notifications.signals
        self.assertIn('notifications.signals', sys.modules)
        self.assertTrue(getattr(notifications.signals, 'SIGNALS_LOADED', False))


class Phase3PreSaveSignalTestCase(TestCase):
    """
    Phase 3 unit tests: Validate pre_save automatic slug generation on Post.
    """

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

        # Clear slug and update title
        post.slug = ""
        post.title = "Updated New Title"
        post.save()
        self.assertEqual(post.slug, slugify("Updated New Title"))


class Phase4PostSaveSignalTestCase(TestCase):
    """
    Phase 4 unit tests: Validate post_save welcome notification on User creation.
    """

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
