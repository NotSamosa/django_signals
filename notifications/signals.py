"""
Django signal handlers for the notifications application.

- Phase 3: pre_save (automatic slug generation for Post)
"""

import logging
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.text import slugify

from notifications.models import Post

logger = logging.getLogger(__name__)

SIGNALS_LOADED = True


# ---------------------------------------------------------------------------
# Phase 3: pre_save - Automatic Slug Generation
# ---------------------------------------------------------------------------
@receiver(pre_save, sender=Post)
def auto_generate_slug_on_pre_save(sender, instance, **kwargs):
    """
    Auto-generates a URL slug using slugify(instance.title) only if slug is empty.

    RECURSION PREVENTION:
    We modify instance.slug directly on the model instance in memory.
    We NEVER call instance.save() inside a pre_save receiver; doing so would
    re-trigger pre_save and cause infinite recursion (RecursionError).
    Because pre_save executes immediately before the SQL INSERT/UPDATE is issued,
    in-memory mutations on 'instance' are automatically persisted by the current save.
    """
    if not instance.slug:
        instance.slug = slugify(instance.title)
        print(f"[PRE-SAVE] Auto-generated slug '{instance.slug}' for Post '{instance.title}'")
