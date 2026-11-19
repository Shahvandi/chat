import asyncio

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .presence import (
    get_online_snapshot,
    register_connection,
    refresh_connection,
    remove_connection,
    sweep_expired_connections,
)


class PresenceConsumer(AsyncJsonWebsocketConsumer):

    HEARTBEAT_INTERVAL = 15
    HEARTBEAT_TIMEOUT = 45
    SWEEP_INTERVAL = 10

    sweeper_task = None

    async def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close(code=4401)
            return

        self.user_id = str(user.pk)
        self.connection_id = self.channel_name
        self.last_seen = asyncio.get_running_loop().time()
        self.heartbeat_task = None

        self.notification_group = f"user.{self.user_id}"

        await self.channel_layer.group_add(
            "presence",
            self.channel_name,
        )
        await self.channel_layer.group_add(
            self.notification_group,
            self.channel_name,
        )

        try:
            became_online, version = await register_connection(
                self.user_id,
                self.connection_id,
            )

            await self.broadcast_expired_users()

            snapshot = await get_online_snapshot()
            await self.accept()

            await self.send_json({
                "type": "presence.snapshot",
                "users": snapshot,
            })

            if became_online:
                await self.broadcast_status(
                    is_online=True,
                    version=version,
                )

            if (
                self.__class__.sweeper_task is None
                or self.__class__.sweeper_task.done()
            ):
                self.__class__.sweeper_task = asyncio.create_task(
                    self.presence_sweeper()
                )

            self.heartbeat_task = asyncio.create_task(
                self.heartbeat_watchdog()
            )

        except Exception:
            await self.channel_layer.group_discard(
                "presence",
                self.channel_name,
            )
            await self.channel_layer.group_discard(
                self.notification_group,
                self.channel_name,
            )
            raise

    async def receive_json(self, content, **kwargs):
        if content.get("type") != "heartbeat":
            return

        self.last_seen = asyncio.get_running_loop().time()

        await refresh_connection(
            self.user_id,
            self.connection_id,
        )

    async def force_disconnect(self, event):
        await self.close(code=4401)

    async def heartbeat_watchdog(self):
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)

                elapsed = (
                    asyncio.get_running_loop().time() - self.last_seen
                )

                if elapsed > self.HEARTBEAT_TIMEOUT:
                    await self.close(code=4408)
                    return

        except asyncio.CancelledError:
            pass

    async def presence_sweeper(self):
        try:
            while True:
                await asyncio.sleep(self.SWEEP_INTERVAL)
                await self.broadcast_expired_users()

        except asyncio.CancelledError:
            pass

        except Exception:
            await asyncio.sleep(self.SWEEP_INTERVAL)
            if not asyncio.current_task().cancelled():
                self.__class__.sweeper_task = asyncio.create_task(
                    self.presence_sweeper()
                )

    async def broadcast_expired_users(self):
        expired_users = await sweep_expired_connections()

        for user_id, version in expired_users:
            await self.channel_layer.group_send(
                "presence",
                {
                    "type": "presence.update",
                    "user_id": user_id,
                    "is_online": False,
                    "version": version,
                },
            )

    async def disconnect(self, close_code):
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

        user_id = getattr(self, "user_id", None)
        connection_id = getattr(self, "connection_id", None)

        if user_id and connection_id:
            try:
                became_offline, version = await remove_connection(
                    user_id,
                    connection_id,
                )

                if became_offline:
                    await self.broadcast_status(
                        is_online=False,
                        version=version,
                    )

            finally:
                await self.channel_layer.group_discard(
                    "presence",
                    self.channel_name,
                )

                notification_group = getattr(
                    self,
                    "notification_group",
                    None,
                )
                if notification_group:
                    await self.channel_layer.group_discard(
                        notification_group,
                        self.channel_name,
                    )

    async def broadcast_status(self, is_online, version):
        await self.channel_layer.group_send(
            "presence",
            {
                "type": "presence.update",
                "user_id": self.user_id,
                "is_online": is_online,
                "version": version,
            },
        )

    async def presence_update(self, event):
        await self.send_json({
            "type": "presence.update",
            "user_id": event["user_id"],
            "is_online": event["is_online"],
            "version": event.get("version", 0),
        })

    async def chat_message(self, event):
        await self.send_json({
            "type": "chat.message",
            "message": event["message"],
        })

    async def chat_conversation(self, event):
        await self.send_json({
            'type': 'chat.conversation',
            'conversation': event['conversation'],
        })
