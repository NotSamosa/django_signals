import logging
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify

from notifications.models import Post, DeletedPost

logger = logging.getLogger(__name__)

SIGNALS_LOADED = True


@receiver(pre_save, sender=Post)
def auto_generate_slug_on_pre_save(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = slugify(instance.title)
        print(f"[PRE-SAVE] Auto-generated slug '{instance.slug}' for Post '{instance.title}'")


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


def post_delete_post_handler(sender, instance, **kwargs):
    msg = f"[POST-DELETE] Post '{instance.title}' (ID: {instance.pk}) was deleted from database."
    print(msg)
    logger.info(msg)


post_delete.connect(post_delete_post_handler, sender=Post, dispatch_uid="post_delete_post_manual")


@receiver(m2m_changed, sender=Post.tags.through)
def track_post_tags_changes(sender, instance, action, pk_set, **kwargs):
    if action in ["pre_add", "post_remove"]:
        now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")
        pk_list = sorted(list(pk_set)) if pk_set else []
        log_msg = f"[{now_str}] [M2M TRACKING] Action: '{action}' | Instance: Post '{instance.title}' (ID: {instance.pk}) | Affected Tag PKs: {pk_list}"
        print(log_msg)
        logger.info(log_msg)
