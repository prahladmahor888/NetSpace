from django.contrib import admin
from NetSpace.models import *
# Register your models here.
admin.site.register(UserPosts)
admin.site.register(UserStory)
admin.site.register(PostLike)
admin.site.register(PostComment)
admin.site.register(PostShare)
admin.site.register(Repost)
admin.site.register(VoiceCall)
admin.site.register(VideoCall)
admin.site.register(Rooms)
admin.site.register(RoomMessage)
