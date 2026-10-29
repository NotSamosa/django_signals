from django.db import models
from django.utils import timezone


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name


class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, blank=True, unique=True)
    content = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'

    def __str__(self):
        return self.title


class DeletedPost(models.Model):
    original_post_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Primary key of the original Post before deletion"
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, blank=True)
    content = models.TextField(blank=True)
    deleted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-deleted_at']
        verbose_name = 'Deleted Post'
        verbose_name_plural = 'Deleted Posts'

    def __str__(self):
        return f"Deleted: {self.title} (Original ID: {self.original_post_id})"
