from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

from . import views

urlpatterns = [
    path("home", views.home, name="home"),
    path('rooms/', views.rooms, name='rooms'),
    path("users/", views.users, name="users"), 
    path('settings/', views.settings, name='settings'),
    path('settings/change-password/', views.change_password, name='change_password'),
    path('notifications/', views.notifications, name='notifications'),
    path("user/<str:username>/", views.user_profile, name="user_profile"),
    path("user_profile/", views.user_profile, name="user_profile"),
    path("user_chats/", views.user_chats, name="user_chats"),
    path('post/upload/', views.post_upload, name='post_upload'),
    path("messages/<int:user_id>/", views.get_messages, name="get_messages"),
    path('post/like/', views.like_post, name='like_post'),
    path('post/comment/', views.add_comment, name='add_comment'),
    path('post/<int:post_id>/comments/', views.get_comments, name='get_comments'),
    path('share-post/', views.share_post, name='share_post'),
    path('repost-post/', views.repost_post, name='repost_post'),
    path('delete-comment/', views.delete_comment, name='delete_comment'),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    path('profile/', views.user_profile, name='own_profile'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('story/upload/', views.upload_story, name='upload_story'),
    path('stories/', views.get_stories, name='get_stories'),
    path('story/view/<int:story_id>/', views.view_story, name='view_story'),
    path('add_comment/', views.add_comment, name='add_comment'),
    path('get_comments/<int:post_id>/', views.get_comments, name='get_comments'),
    path('call/initiate/', views.initiate_call, name='initiate_call'),
    path('call/end/', views.end_call, name='end_call'),
    path('call/history/<int:user_id>/', views.get_call_history, name='call_history'),
    path('call/active/', views.get_active_call, name='get_active_call'),
    path('call/status/update/', views.update_call_status, name='update_call_status'),
    path('create-room/', views.create_room, name='create_room'),
    path('room/<int:room_id>/join/', views.join_room, name='join_room'),
    path('room/<int:room_id>/messages/', views.room_messages, name='room_messages'),
    path('room/<int:room_id>/leave/', views.leave_room, name='leave_room'),
    path('ai/chat/', views.ai_chat, name='ai_chat'),
    path('ai/chat/history/', views.get_ai_chat_history, name='ai_chat_history'),
    path('posts/<int:post_id>/likes/', views.get_post_likes, name='get_post_likes'),
    path('posts/<int:post_id>/comments/', views.get_post_comments, name='get_post_comments'),
    path('posts/<int:post_id>/reposts/', views.get_post_reposts, name='get_post_reposts'),
    path('post_detail', views.post_detail, name='get_post_details'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('.well-known/appspecific/com.chrome.devtools.json', 
         lambda r: HttpResponse(status=204), 
         name='chrome-devtools'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)