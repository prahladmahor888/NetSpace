from django.db import models
from Accounts.models import CustomUser
from django.utils import timezone
import os
import uuid

def post_image_path(instance, filename):
    # Get file extension
    ext = os.path.splitext(filename)[1]
    # Generate unique filename
    unique_filename = f"post_{uuid.uuid4().hex[:8]}{ext}"
    # Return path relative to MEDIA_ROOT
    return os.path.join('posts', unique_filename)

def generate_room_id():
    return str(uuid.uuid4().hex[:15])

def generate_room_code():
    return str(uuid.uuid4().hex[:6]).upper()

class Message(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

class VideoCall(models.Model):
    caller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='video_calls_made')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='video_calls_received')
    call_time = models.DateTimeField(auto_now_add=True)
    duration = models.DurationField(null=True, blank=True)  # Duration of the call

    class Meta:
        ordering = ['-call_time']
        verbose_name = 'Video Call'
        verbose_name_plural = 'Video Calls'

    def __str__(self):
        return f"Call from {self.caller.username} to {self.receiver.username} at {self.call_time}" if self.caller and self.receiver else "Video Call without users"
    
class VoiceCall(models.Model):
    caller = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='voice_calls_made')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='voice_calls_received')
    call_time = models.DateTimeField(auto_now_add=True)
    duration = models.DurationField(null=True, blank=True)  # Duration of the call

    class Meta:
        ordering = ['-call_time']
        verbose_name = 'Voice Call'
        verbose_name_plural = 'Voice Calls'

    def __str__(self):
        return f"Call from {self.caller.username} to {self.receiver.username} at {self.call_time}" if self.caller and self.receiver else "Voice Call without users"


# Create your models here.
class UserPosts(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived')
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='posts')
    post_content = models.TextField()
    post_image = models.ImageField(upload_to=post_image_path, null=True, blank=True)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    reposts_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='published')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Post'
        verbose_name_plural = 'User Posts'

    def __str__(self):
        return f"{self.user.username}'s post" if self.user else "Post without user"

    def increment_likes(self):
        self.likes_count += 1
        self.save()

    def increment_comments(self):
        self.comments_count += 1
        self.save()

    def increment_shares(self):
        self.shares_count += 1
        self.save()

    def increment_reposts(self):
        self.reposts_count += 1
        self.save()
        
class PostLike(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(UserPosts, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']

class PostComment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(UserPosts, on_delete=models.CASCADE, related_name='post_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

class PostShare(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='shares')
    post = models.ForeignKey(UserPosts, on_delete=models.CASCADE, related_name='post_shares')
    share_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class Repost(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reposts')
    original_post = models.ForeignKey(UserPosts, on_delete=models.CASCADE, related_name='post_reposts')
    repost_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'original_post')


class UserStory(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='stories')
    story_content = models.TextField()
    story_image = models.ImageField(upload_to='story_images', null=True, blank=True)
    story_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    is_seen = models.BooleanField(default=False)
    is_shared = models.BooleanField(default=False)
    is_liked = models.BooleanField(default=False)
    is_commented = models.BooleanField(default=False)    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Story'
        verbose_name_plural = 'User Stories'

    def __str__(self):
        return f"{self.user.username}'s story" if self.user else "Story without user"
    
    def increment_story_count(self):
        self.story_count += 1
        self.save()

    def mark_as_seen(self):
        self.is_seen = True
        self.save()

    def mark_as_shared(self):
        self.is_shared = True
        self.save()

    def mark_as_liked(self):
        self.is_liked = True
        self.save()

    def mark_as_commented(self):
        self.is_commented = True
        self.save()

    def mark_as_deleted(self):
        self.is_deleted = True
        self.save()

    def mark_as_active(self):
        self.is_active = True
        self.save()

    def mark_as_inactive(self):
        self.is_active = False
        self.save()

    def mark_as_expired(self):
        self.is_active = False
        self.expires_at = timezone.now()
        self.save()
    
class StoryLike(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='story_likes')
    story = models.ForeignKey(UserStory, on_delete=models.CASCADE, related_name='story_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'story')
        ordering = ['-created_at']

class StoryComment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='story_comments')
    story = models.ForeignKey(UserStory, on_delete=models.CASCADE, related_name='story_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

class StoryShare(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='story_shares')
    story = models.ForeignKey(UserStory, on_delete=models.CASCADE, related_name='story_shares')
    share_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'story')
        verbose_name = 'Story Share'
        verbose_name_plural = 'Story Shares'

class StoryView(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='story_views')
    story = models.ForeignKey(UserStory, on_delete=models.CASCADE, related_name='story_views')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'story')
        ordering = ['-created_at']
        verbose_name = 'Story View'
        verbose_name_plural = 'Story Views'


class Rooms(models.Model):
    CATEGORY_CHOICES = [
        ('gaming', 'Gaming'),
        ('education', 'Education'),
        ('music', 'Music'),
        ('general', 'General'),
        ('technology', 'Technology'),
        ('sports', 'Sports'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('closed', 'Closed'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='rooms')
    room_id = models.CharField(max_length=15, unique=True, null=True, blank=True)
    room_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    room_name = models.CharField(max_length=100)
    room_description = models.TextField()
    room_image = models.ImageField(upload_to='room_images', null=True, blank=True)
    room_type = models.CharField(max_length=50, choices=[('public', 'Public'), ('private', 'Private')])
    room_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    room_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    participant_count = models.PositiveIntegerField(default=0)
    max_participants = models.PositiveIntegerField(default=100)
    is_featured = models.BooleanField(default=False)
    password = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Room'
        verbose_name_plural = 'Rooms'

    def __str__(self):
        return self.room_name if self.room_name else "Room without name"

    @classmethod
    def create_unique_code(cls):
        code = generate_room_code()
        while cls.objects.filter(room_code=code).exists():
            code = generate_room_code()
        return code

    def save(self, *args, **kwargs):
        if not self.room_id:
            while True:
                generated_id = generate_room_id()
                if not Rooms.objects.filter(room_id=generated_id).exists():
                    self.room_id = generated_id
                    break

        if not self.room_code:
            while True:
                generated_code = generate_room_code()
                if not Rooms.objects.filter(room_code=generated_code).exists():
                    self.room_code = generated_code
                    break

        super().save(*args, **kwargs)

    def join_room(self, user):
        if self.participant_count < self.max_participants:
            self.participant_count += 1
            self.save()
            return True
        return False

    def leave_room(self):
        if self.participant_count > 0:
            self.participant_count -= 1
            self.save()

class RoomMessage(models.Model):
    room = models.ForeignKey(Rooms, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey('Accounts.CustomUser', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        # Existing follow notifications
        ('follow', 'Follow'),
        ('follow_request', 'Follow Request'),
        ('follow_accept', 'Follow Request Accepted'),
        ('follow_back', 'Follow Back'),
        ('follow_request_rejected', 'Follow Request Rejected'),
        ('new_follower', 'New Follower'),
        ('unfollow', 'Unfollowed'),
        # New notification types
        ('new_post', 'New Post'),
        ('post_like', 'Post Like'),
        ('post_comment', 'Post Comment'),
        ('post_share', 'Post Share'),
        ('post_repost', 'Post Repost'),
        ('live_stream', 'Live Stream Started'),
    ]

    from_user = models.ForeignKey(CustomUser, related_name='notifications_sent', on_delete=models.CASCADE)
    to_user = models.ForeignKey(CustomUser, related_name='notifications_received', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_post = models.ForeignKey('UserPosts', on_delete=models.CASCADE, null=True, blank=True)
    comment_content = models.TextField(null=True, blank=True)  # Store comment content for comment notifications

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.from_user} to {self.to_user}: {self.notification_type}'

    @classmethod
    def create_follow_notification(cls, from_user, to_user, notification_type):
        """Create a follow-related notification"""
        return cls.objects.create(
            from_user=from_user,
            to_user=to_user,
            notification_type=notification_type
        )

    @classmethod
    def send_follow_request(cls, from_user, to_user):
        """Send a follow request notification"""
        return cls.create_follow_notification(from_user, to_user, 'follow_request')

    @classmethod
    def accept_follow_request(cls, from_user, to_user):
        """Send a follow request accepted notification"""
        return cls.create_follow_notification(from_user, to_user, 'follow_accept')

    @classmethod
    def new_follower(cls, from_user, to_user):
        """Send a new follower notification"""
        return cls.create_follow_notification(from_user, to_user, 'new_follower')

    @classmethod
    def reject_follow_request(cls, from_user, to_user):
        """Send a follow request rejected notification"""
        return cls.create_follow_notification(from_user, to_user, 'follow_request_rejected')

    @classmethod
    def notify_new_post(cls, from_user, to_user, post):
        """Notify followers about a new post"""
        return cls.objects.create(
            from_user=from_user,
            to_user=to_user,
            notification_type='new_post',
            related_post=post
        )

    @classmethod
    def notify_post_like(cls, from_user, to_user, post):
        """Notify about post like"""
        return cls.objects.create(
            from_user=from_user,
            to_user=to_user,
            notification_type='post_like',
            related_post=post
        )

    @classmethod
    def notify_post_comment(cls, from_user, to_user, post, comment_content):
        """Notify about post comment with the comment content"""
        return cls.objects.create(
            from_user=from_user,
            to_user=to_user,
            notification_type='post_comment',
            related_post=post,
            comment_content=comment_content
        )

    @classmethod
    def notify_post_share(cls, from_user, to_user, post):
        """Notify about post share"""
        return cls.objects.create(
            from_user=from_user,
            to_user=to_user,
            notification_type='post_share',
            related_post=post
        )

    @classmethod
    def notify_post_repost(cls, from_user, to_user, post):
        """Notify about post repost"""
        return cls.objects.create(
            from_user=from_user,
            to_user=to_user,
            notification_type='post_repost',
            related_post=post
        )

    @classmethod
    def notify_live_stream(cls, from_user, to_user):
        """Notify followers about live stream"""
        return cls.objects.create(
            from_user=from_user,
            to_user=to_user,
            notification_type='live_stream'
        )