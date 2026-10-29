"""
Django signal handlers for the notifications application.

- Phase 3: pre_save (automatic slug generation for Post)
- Phase 4: post_save (user welcome notification for User)
"""

import logging
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save
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


# ---------------------------------------------------------------------------
# Phase 4: Helper Function - Welcome Email Dispatch
# ---------------------------------------------------------------------------
def send_welcome_email(user_email: str) -> None:
    """
    Dummy notification function simulating welcome email delivery.
    Uses print statement as requested.
    """
    msg = f"[EMAIL NOTIFICATION] Welcome email sent to: {user_email}"
    print(msg)
    logger.info(msg)


# ---------------------------------------------------------------------------
# Phase 4: post_save - User Welcome Notification
# ---------------------------------------------------------------------------
@receiver(post_save, sender=User)
def user_welcome_notification(sender, instance, created, **kwargs):
    """
    Sends a welcome email when a new User record is created.

    RECURSION PREVENTION & EFFICIENCY:
    1. Checks the boolean 'created' flag. Django passes created=True only when
       a new database record was inserted. On subsequent updates (e.g. password
       updates, profile edits), created is False, preventing duplicate emails.
    2. Does NOT call instance.save() inside this receiver, preventing an
       infinite post_save loop.
    """
    if created:
        recipient = instance.email if instance.email else instance.username
        print(f"[POST-SAVE] New user created (ID: {instance.pk}, Username: '{instance.username}').")
        send_welcome_email(recipient)
