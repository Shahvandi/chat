from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Message, Conversation


@receiver(
    post_save,
    sender=Message,
    dispatch_uid="chats.update_conversation_after_message"
)
def update_conversation_after_message(
    sender,
    instance,
    created,
    **kwargs
):
    """
    Update conversation activity timestamp only
    when a new message is created.

    This signal does not send WebSocket events.
    """

    if not created:
        return

    Conversation.objects.filter(
        pk=instance.conversation_id
    ).update(
        updated_at=timezone.now()
    )
