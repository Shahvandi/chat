from channels.generic.websocket import AsyncJsonWebsocketConsumer


class PresenceConsumer(AsyncJsonWebsocketConsumer):

    # user_id: {
    #     "channels": set(),
    #     "name": str
    # }
    online_users = {}

    async def connect(self):

        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4401)
            return

        self.user_id = str(user.pk)

        self.user_name = (
            f"{user.first_name} {user.last_name}".strip()
            or user.mobile
        )

        # گروه عمومی حضور کاربران
        await self.channel_layer.group_add(
            "presence",
            self.channel_name
        )

        # گروه اختصاصی اعلان‌های این کاربر
        self.notification_group = f"user.{self.user_id}"

        await self.channel_layer.group_add(
            self.notification_group,
            self.channel_name
        )

        await self.accept()

        already_online = self.user_id in self.online_users

        if not already_online:
            self.online_users[self.user_id] = {
                "channels": set(),
                "name": self.user_name,
            }

        self.online_users[self.user_id]["channels"].add(
            self.channel_name
        )

        # ارسال وضعیت کاربران آنلاین
        await self.send_json({
            "type": "presence.snapshot",
            "users": [
                {
                    "user_id": user_id,
                    "name": data["name"],
                }
                for user_id, data in self.online_users.items()
            ],
        })

        if not already_online:
            await self.broadcast_status(True)

    async def disconnect(self, close_code):

        user_id = getattr(self, "user_id", None)

        if user_id:

            user_data = self.online_users.get(user_id)

            if user_data:

                user_data["channels"].discard(
                    self.channel_name
                )

                if not user_data["channels"]:

                    self.online_users.pop(user_id, None)

                    await self.broadcast_status(False)

        await self.channel_layer.group_discard(
            "presence",
            self.channel_name
        )

        notification_group = getattr(
            self,
            "notification_group",
            None
        )

        if notification_group:

            await self.channel_layer.group_discard(
                notification_group,
                self.channel_name
            )

    async def broadcast_status(self, is_online):

        await self.channel_layer.group_send(
            "presence",
            {
                "type": "presence.update",
                "user_id": self.user_id,
                "name": self.user_name,
                "is_online": is_online,
            }
        )

    async def presence_update(self, event):

        await self.send_json({
            "type": "presence.update",
            "user_id": event["user_id"],
            "name": event["name"],
            "is_online": event["is_online"],
        })

    # دریافت اعلان پیام جدید
    async def chat_message(self, event):

        await self.send_json({
            "type": "chat.message",
            "message": event["message"],
        })
