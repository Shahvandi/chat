from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from .models import Conversation, Message


class MessageSignalTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            mobile="09120000001",
            password="test12345",
            first_name="Test",
            last_name="User"
        )

        self.conversation = Conversation.objects.create(
            title="Test Chat",
            type=Conversation.ConversationType.PRIVATE,
            created_by=self.user,
            private_key="test-private-chat"
        )

    def test_message_creation_updates_conversation(self):

        old_time = timezone.now() - timedelta(days=2)

        Conversation.objects.filter(
            pk=self.conversation.pk
        ).update(updated_at=old_time)

        Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            content="Hello"
        )

        self.conversation.refresh_from_db()

        self.assertGreater(
            self.conversation.updated_at,
            old_time
        )

    def test_message_update_does_not_trigger_activity_signal(self):

        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            content="Original"
        )

        old_time = timezone.now() - timedelta(days=1)

        Conversation.objects.filter(
            pk=self.conversation.pk
        ).update(updated_at=old_time)

        message.content = "Edited"
        message.save()

        self.conversation.refresh_from_db()

        self.assertEqual(
            self.conversation.updated_at,
            old_time
        )



# ###############################################

from unittest.mock import MagicMock, patch
from django.test import TestCase

from .views import broadcast_message_notification


class MessageNotificationTests(TestCase):

    @patch("chats.views.async_to_sync")
    @patch("chats.views.get_channel_layer")
    def test_notification_is_sent_to_user_groups(
        self,
        get_channel_layer_mock,
        async_to_sync_mock
    ):
        channel_layer = MagicMock()
        get_channel_layer_mock.return_value = channel_layer

        group_send_mock = MagicMock()
        async_to_sync_mock.return_value = group_send_mock

        user_ids = [10, 20, 30]

        payload = {
            "id": "message-123",
            "content": "Hello",
            "sender_id": "10",
            "sender_name": "Test User",
            "conversation_id": "conversation-123",
        }

        broadcast_message_notification(user_ids, payload)

        self.assertEqual(async_to_sync_mock.call_count, 3)
        self.assertEqual(group_send_mock.call_count, 3)

        called_groups = [
            call.args[0]
            for call in group_send_mock.call_args_list
        ]

        self.assertEqual(
            called_groups,
            ["user.10", "user.20", "user.30"]
        )

        for call in group_send_mock.call_args_list:
            self.assertEqual(
                call.args[1]["type"],
                "chat.message"
            )

            self.assertEqual(
                call.args[1]["message"],
                payload
            )
