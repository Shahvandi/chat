import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Conversation(models.Model):

    class ConversationType(models.TextChoices):
        PRIVATE = 'PRIVATE', 'Private'
        GROUP = 'GROUP', 'Group'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    title = models.CharField(
        max_length=150,
        blank=True,
        default=''
    )

    private_key = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )

    type = models.CharField(
        max_length=10,
        choices=ConversationType.choices,
        default=ConversationType.PRIVATE
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_conversations'
    )

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ConversationMember',
        related_name='conversations'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f'Conversation {self.id}'


class ConversationMember(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='members'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversation_memberships'
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    last_read_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_muted = models.BooleanField(default=False)

    class Meta:
        db_table = 'conversation_members'
        constraints = [
            models.UniqueConstraint(
                fields=['conversation', 'user'],
                name='unique_conversation_member'
            )
        ]

    def __str__(self):
        return f'{self.user} - {self.conversation}'

    @property
    def display_title(self):

        conversation = self.conversation

        if conversation.type == Conversation.ConversationType.GROUP:
            return conversation.title or 'گروه بدون عنوان'

        other_member = next(
            (
                member
                for member in conversation.members.all()
                if member.user_id != self.user_id
            ),
            None
        )

        if other_member is None:
            return conversation.title or 'پیام‌های شخصی'

        user = other_member.user

        return (
            f'{user.first_name} {user.last_name}'.strip()
            or getattr(user, 'mobile', '')
            or 'کاربر'
        )


class Message(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    edited_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']
        indexes = [
            models.Index(
                fields=['conversation', 'created_at'],
                name='message_conversation_date_idx'
            )
        ]

    def __str__(self):
        return f'{self.sender} - {self.created_at}'