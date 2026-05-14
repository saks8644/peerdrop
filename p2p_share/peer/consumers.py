import json
from channels.generic.websocket import AsyncWebsocketConsumer

class PeerStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join a group for broadcasting updates
        await self.channel_layer.group_add("peer_status", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the group
        await self.channel_layer.group_discard("peer_status", self.channel_name)

    async def receive(self, text_data):
        # Optionally handle messages from the client
        data = json.loads(text_data)
        # For example, broadcast a message to the group
        await self.channel_layer.group_send(
            "peer_status",
            {
                "type": "peer_status_update",
                "message": data.get("message", "")
            }
        )

    async def peer_status_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "message": event["message"]
        }))