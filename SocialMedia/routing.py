from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from NetSpace.consumers import CallConsumer
from django.urls import re_path
from NetSpace import routing as netspace_routing

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter([
            re_path(r'ws/call/(?P<user_id>\w+)/$', CallConsumer.as_asgi()),
            *netspace_routing.websocket_urlpatterns
        ])
    ),
})
