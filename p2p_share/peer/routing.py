from django.urls import path

from . import consumers


websocket_urlpatterns = [
    path('ws/peer-status/', consumers.PeerStatusConsumer.as_asgi()),
]
