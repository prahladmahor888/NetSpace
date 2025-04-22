from django.db import models
from django.contrib.auth.models import AbstractUser
from .manager import CustomUserManager
from django.utils import timezone
from django.core.exceptions import ValidationError

# Create your models here.

class CustomUser(AbstractUser):
    username = models.CharField(unique=True, max_length=50)
    email = models.EmailField(unique=True)
    user_id = models.CharField(max_length=15, unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    user_bio = models.TextField(max_length=500, blank=True)
    nickname = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics', null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    email_notifications = models.BooleanField(default=False)
    user_place = models.CharField(max_length=100, blank=True)
    user_website = models.URLField(max_length=200, blank=True)
    user_occupation = models.CharField(max_length=100, blank=True)
    user_education = models.CharField(max_length=100, blank=True)
    user_interests = models.CharField(max_length=200, blank=True)
    is_private = models.BooleanField(default=False)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phone_number', 'gender']
    objects = CustomUserManager()

class UserFollowing(models.Model):
    user = models.ForeignKey(CustomUser, related_name='following', on_delete=models.CASCADE)
    following_user = models.ForeignKey(CustomUser, related_name='followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'following_user')


class BlockUserManager(models.Manager):
    def get_active_blocks(self):
        return self.filter(status='active')
    
    def get_user_blocks(self, user):
        return self.filter(user=user, status='active')
    
    def is_blocked(self, user, blocked_user):
        return self.filter(
            user=user, 
            blocked_user=blocked_user, 
            status='active'
        ).exists()

class BlockUser(models.Model):
    BLOCK_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
        ('appealed', 'Appealed')
    ]
    
    BLOCK_TYPES = [
        ('harassment', 'Harassment'),
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('other', 'Other')
    ]
    
    user = models.ForeignKey(CustomUser, related_name='blocked_users', on_delete=models.CASCADE)
    blocked_user = models.ForeignKey(CustomUser, related_name='blocked_by_users', on_delete=models.CASCADE)
    reason = models.TextField(max_length=500, blank=True, null=True)
    block_type = models.CharField(max_length=20, choices=BLOCK_TYPES, default='other')
    status = models.CharField(max_length=10, choices=BLOCK_STATUS, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    unblocked_at = models.DateTimeField(null=True, blank=True)
    block_duration = models.DurationField(null=True, blank=True, help_text="Duration of the block, null means indefinite")
    report_count = models.PositiveIntegerField(default=0)
    is_permanent = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    objects = BlockUserManager()

    class Meta:
        unique_together = ('user', 'blocked_user')
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['blocked_user', 'status']),
            models.Index(fields=['block_type', 'status']),
        ]
        
    def __str__(self):
        return f"{self.user.username} blocked {self.blocked_user.username} - {self.get_block_type_display()}"

    def clean(self):
        if self.user == self.blocked_user:
            raise ValidationError("Users cannot block themselves")
        if self.is_permanent and self.block_duration:
            raise ValidationError("Permanent blocks cannot have a duration")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_block_expired(self):
        if self.is_permanent or not self.block_duration:
            return False
        return (timezone.now() - self.created_at) > self.block_duration

    def unblock(self, reason=None):
        self.status = 'inactive'
        self.unblocked_at = timezone.now()
        if reason:
            self.reason += f"\nUnblocked: {reason}"
        self.save()

    def make_permanent(self):
        self.is_permanent = True
        self.block_duration = None
        self.save()

    def increment_report_count(self):
        self.report_count += 1
        self.save()

    def appeal_block(self):
        if self.status == 'active':
            self.status = 'appealed'
            self.save()