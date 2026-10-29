from django.test import TestCase
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
