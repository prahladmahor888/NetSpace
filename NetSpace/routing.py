from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/call/(?P<call_id>\w+)/$', consumers.CallConsumer.as_asgi()),
    re_path(r'ws/call/$', consumers.CallConsumer.as_asgi()),
    re_path(r'ws/call/user/(?P<user_id>\w+)/$', consumers.CallConsumer.as_asgi()),
    re_path(r'ws/call/(?P<user_id>\w+)/$', consumers.CallConsumer.as_asgi()),
]
