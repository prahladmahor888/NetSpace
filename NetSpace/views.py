from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, F
from Accounts.models import CustomUser as User, UserFollowing
from django.http import JsonResponse
import re
from Accounts.models import UserFollowing as Follow
from .models import Message, UserPosts, PostLike, PostComment, PostShare, Repost, UserStory, VideoCall, VoiceCall, Rooms, RoomMessage, Notification
from django.utils import timezone
from datetime import timedelta
import json
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from django.conf import settings
from SocialMedia.settings import DEFAULT_PROFILE_PIC
from django.views.decorators.csrf import csrf_exempt


# Create your views here.
@login_required(login_url='login')
def home(request):
    following = UserFollowing.objects.filter(user=request.user).values_list('following_user', flat=True)
    
    # Get active stories from followed users and current user
    active_stories = UserStory.objects.filter(
        Q(user__in=following) | Q(user=request.user),
        is_active=True,
        is_deleted=False,
        expires_at__gt=timezone.now()
    ).select_related('user').order_by('-created_at')

    stories = []
    for story in active_stories:
        stories.append({
            'id': story.id,
            'user': {
                'id': story.user.id,
                'username': story.user.username,
                'profile_picture': story.user.profile_picture.url if story.user.profile_picture else settings.DEFAULT_PROFILE_PIC
            },
            'content': story.story_content,
            'image': story.story_image if story.story_image else None,
            'created_at': story.created_at,
            'expires_at': story.expires_at,
            'views_count': story.story_count,
            'is_seen': story.is_seen,
            'is_own_story': story.user == request.user
        })

    # Get posts with likes and comments counts
    raw_posts = UserPosts.objects.filter(
        Q(user__in=following) | Q(user=request.user)
    ).select_related('user').prefetch_related('post_likes', 'post_comments', 'post_shares', 'post_reposts').order_by('-created_at')

    posts = []
    for post in raw_posts:
        user_data = {
            'id': post.user.id,
            'username': post.user.username,
            'profile_picture': DEFAULT_PROFILE_PIC
        }
        
        # Get counts for likes and comments
        likes_count = post.post_likes.count()
        comments_count = post.post_comments.count()
        shares_count = post.post_shares.count()
        reposts_count = post.post_reposts.count()
        
        posts.append({
            'id': post.id,
            'user': user_data,
            'content': post.post_content,
            'image': post.post_image if post.post_image else None,
            'created_at': post.created_at,
            'is_own_post': post.user == request.user,
            'likes': likes_count,
            'comments': comments_count,
            'shares': shares_count,
            'reposts': reposts_count,
            'is_liked': post.post_likes.filter(user=request.user).exists(),
            'is_shared': post.post_shares.filter(user=request.user).exists(),
            'is_reposted': post.post_reposts.filter(user=request.user).exists()
        })
    
    context = {
        'posts': posts,
        'following': following,
        'stories': active_stories,
        'DEFAULT_PROFILE_PIC': DEFAULT_PROFILE_PIC,
    }
    return render(request, 'index.html', context)

def post_upload(request):
    if request.method == 'POST':
        try:
            post_content = request.POST.get('post_content', '').strip()
            
            # Check if request is AJAX
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
            # Validate post content
            if not post_content:
                messages.error(request, 'Post content cannot be empty!')
                return JsonResponse({'status': 'error', 'message': 'Post content cannot be empty'}) if is_ajax else redirect('home')
            
            image_url = None
            if 'post_image' in request.FILES:
                post_image = request.FILES['post_image']
                # Validate image type
                allowed_types = ['image/jpeg', 'image/png', 'image/gif']
                if post_image.content_type not in allowed_types:
                    messages.error(request, 'Invalid image type. Please upload JPEG, PNG or GIF.')
                    return JsonResponse({'status': 'error', 'message': 'Invalid image type'}) if is_ajax else redirect('home')
                
                if post_image.size > 5 * 1024 * 1024:  # 5MB limit
                    messages.error(request, 'Image size should be less than 5MB.')
                    return JsonResponse({'status': 'error', 'message': 'Image too large'}) if is_ajax else redirect('home')
                
                fs = FileSystemStorage()
                filename = fs.save(f'posts/{post_image.name}', post_image)
                image_url = fs.url(filename)  # This will add MEDIA_URL prefix
                if not image_url.startswith('/'):
                    image_url = '/' + image_url
            
            # Create post object
            post = UserPosts.objects.create(
                user=request.user,
                post_content=post_content,
                post_image=image_url
            )
            
            # Send notifications to followers
            followers = UserFollowing.objects.filter(following_user=request.user)
            for follower in followers:
                Notification.objects.create(
                    from_user=request.user,
                    to_user=follower.user,
                    notification_type='new_post',
                    related_post=post
                )
            
            messages.success(request, 'Post created successfully!')
            response_data = {
                'status': 'success',
                'message': 'Post created successfully',
                'post_id': post.id,
                'image_url': image_url
            }
            return JsonResponse(response_data) if is_ajax else redirect('home')
            
        except Exception as e:
            error_message = f'Error creating post: {str(e)}'
            messages.error(request, error_message)
            return JsonResponse({'status': 'error', 'message': error_message}) if is_ajax else redirect('home')
    
    return redirect('home')

@login_required(login_url='login')
def user_profile(request, username=None):
    profile_user = get_object_or_404(User, username=username) if username else request.user
    
    # Get list of users that the current user is following
    following_users = UserFollowing.objects.filter(user=request.user).values_list('following_user_id', flat=True)
    
    # Get following status if viewing other's profile
    is_following = UserFollowing.objects.filter(
        user=request.user,
        following_user=profile_user
    ).exists() if request.user != profile_user else False
    
    # Get user stats
    stats = {
        'posts': UserPosts.objects.filter(user=profile_user).count(),
        'followers': UserFollowing.objects.filter(following_user=profile_user).count(),
        'following': UserFollowing.objects.filter(user=profile_user).count(),
        'likes_given': PostLike.objects.filter(user=profile_user).count()
    }
    
    # Get user's posts with engagement data and proper image URLs
    posts = UserPosts.objects.filter(user=profile_user)\
        .select_related('user')\
        .prefetch_related('post_likes', 'post_comments', 'post_shares')\
        .annotate(
            total_likes=Count('post_likes', distinct=True),
            total_comments=Count('post_comments', distinct=True),
            total_shares=Count('post_shares', distinct=True)
        ).order_by('-created_at')

    # Process posts to ensure proper image URLs
    processed_posts = []
    for post in posts:
        post_dict = {
            'id': post.id,
            'user': post.user,
            'content': post.post_content,
            'created_at': post.created_at,
            'total_likes': post.total_likes,
            'total_comments': post.total_comments,
            'total_shares': post.total_shares,
            'image': None,
            'is_liked': PostLike.objects.filter(user=request.user, post=post).exists()
        }
        
        # Handle post image
        if post.post_image:
            try:
                # Remove any potential double slashes and ensure proper URL format
                image_url = post.post_image.url if hasattr(post.post_image, 'url') else post.post_image
                image_url = image_url.replace('/media/media/', '/media/')
                post_dict['image'] = image_url
            except:
                post_dict['image'] = None
        
        processed_posts.append(post_dict)
    
    context = {
        'profile_user': profile_user,
        'stats': stats,
        'posts': processed_posts,  # Use processed posts instead of raw posts
        'is_following': is_following,
        'following': following_users,
        'is_own_profile': request.user == profile_user,
        'DEFAULT_PROFILE_PIC': DEFAULT_PROFILE_PIC
    }
    
    return render(request, 'user_profile.html', context)

@login_required(login_url='login')
def users(request):
    if request.method == 'POST':
        user_to_follow_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        if user_to_follow_id and action:
            try:
                user_to_follow = User.objects.get(id=user_to_follow_id)
                
                if action == 'follow':
                    if user_to_follow.is_private:
                        # For private profiles, create follow request
                        Notification.objects.create(
                            from_user=request.user,
                            to_user=user_to_follow,
                            notification_type='follow_request'
                        )
                        return JsonResponse({
                            'status': 'success',
                            'message': 'Follow request sent',
                            'is_request_sent': True
                        })
                    else:
                        # For public profiles, directly follow
                        following, created = UserFollowing.objects.get_or_create(
                            user=request.user,
                            following_user=user_to_follow
                        )
                        
                        if created:
                            # Create new follower notification
                            Notification.objects.create(
                                from_user=request.user,
                                to_user=user_to_follow,
                                notification_type='new_follower'
                            )
                            
                            # Check if user_to_follow is following the current user
                            if UserFollowing.objects.filter(user=user_to_follow, following_user=request.user).exists():
                                # Create follow back notification
                                Notification.objects.create(
                                    from_user=request.user,
                                    to_user=user_to_follow,
                                    notification_type='follow_back'
                                )
                
                elif action == 'accept_request':
                    # Accept follow request
                    UserFollowing.objects.get_or_create(
                        user=user_to_follow,
                        following_user=request.user
                    )
                    # Create accept notification
                    Notification.objects.create(
                        from_user=request.user,
                        to_user=user_to_follow,
                        notification_type='follow_accept'
                    )
                    # Delete the original follow request notification
                    Notification.objects.filter(
                        from_user=user_to_follow,
                        to_user=request.user,
                        notification_type='follow_request'
                    ).delete()
                
                elif action == 'reject_request':
                    # Create rejection notification
                    Notification.objects.create(
                        from_user=request.user,
                        to_user=user_to_follow,
                        notification_type='follow_request_rejected'
                    )
                    # Delete the original follow request notification
                    Notification.objects.filter(
                        from_user=user_to_follow,
                        to_user=request.user,
                        notification_type='follow_request'
                    ).delete()
                
                elif action == 'unfollow':
                    UserFollowing.objects.filter(
                        user=request.user,
                        following_user=user_to_follow
                    ).delete()
                
                return JsonResponse({'status': 'success'})
            except User.DoesNotExist:
                return JsonResponse({'status': 'error'})

    # Get users the current user is following
    following = UserFollowing.objects.filter(user=request.user).values_list('following_user', flat=True)
    
    # Get suggested users (excluding current user and already followed users)
    suggested_users = User.objects.exclude(
        Q(id=request.user.id) | Q(id__in=following)
    )[:5]  # Limit to 5 suggestions
    
    # Get all users with their following status
    all_users = User.objects.exclude(id=request.user.id)
    users_with_status = [
        {
            'user': user,
            'is_following': user.id in following,
            'is_following_you': UserFollowing.objects.filter(
                user=user,
                following_user=request.user
            ).exists()
        }
        for user in all_users
    ]

    context = {
        'users': users_with_status,
        'suggested_users': suggested_users
    }
    return render(request, 'users.html', context)

@login_required
def user_chats(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        receiver_id = data.get('receiver_id')
        message_content = data.get('message')
        
        if receiver_id and message_content:
            receiver = User.objects.get(id=receiver_id)
            message = Message.objects.create(
                sender=request.user,
                receiver=receiver,
                content=message_content
            )
            return JsonResponse({
                'status': 'success',
                'message': {
                    'content': message.content,
                    'timestamp': message.timestamp.strftime("%I:%M %p"),
                    'sender': request.user.username
                }
            })

    # Get mutual followers
    user_followers = Follow.objects.filter(following_user=request.user).values_list('user', flat=True)
    user_following = Follow.objects.filter(user=request.user).values_list('following_user', flat=True)
    mutual_followers = set(User.objects.filter(id__in=user_followers).filter(id__in=user_following))

    # Get users with message history
    users_with_messages = set(User.objects.filter(
        Q(sent_messages__receiver=request.user) | 
        Q(received_messages__sender=request.user)
    ).exclude(id=request.user.id).distinct())

    # Combine users using sets
    chat_users = list(mutual_followers | users_with_messages)
    
    # Get selected user and their messages
    selected_user_id = request.GET.get('user_id')
    messages = []
    selected_user = None
    
    if selected_user_id:
        selected_user = get_object_or_404(User, id=selected_user_id)
        messages = Message.objects.filter(
            (Q(sender=request.user, receiver=selected_user) |
             Q(sender=selected_user, receiver=request.user))
        ).order_by('timestamp')
        
        Message.objects.filter(sender=selected_user, receiver=request.user, is_read=False).update(is_read=True)
    
    # Enhance chat users with last message and unread count
    enhanced_users = []
    for user in chat_users:
        last_message = Message.objects.filter(
            (Q(sender=request.user, receiver=user) | 
             Q(sender=user, receiver=request.user))
        ).order_by('-timestamp').first()
        
        unread_count = Message.objects.filter(
            sender=user,
            receiver=request.user,
            is_read=False
        ).count()
        
        # Store the message object itself for timestamp access
        user.last_message = last_message.content if last_message else None
        user.last_message_time = last_message.timestamp if last_message else None
        user.unread_count = unread_count
        user.is_mutual_follower = user in mutual_followers
        enhanced_users.append(user)
    
    # Sort users: mutual followers first, then by last message time
    enhanced_users.sort(key=lambda x: (
        not x.is_mutual_follower,
        -(x.last_message_time.timestamp() if x.last_message_time else 0)
    ))
    
    # Get recent calls
    video_calls = VideoCall.objects.filter(
        Q(caller=request.user) | Q(receiver=request.user)
    ).select_related('caller', 'receiver').order_by('-call_time')[:5]
    
    voice_calls = VoiceCall.objects.filter(
        Q(caller=request.user) | Q(receiver=request.user)
    ).select_related('caller', 'receiver').order_by('-call_time')[:5]
    
    # Format call history for each user
    call_history = {}
    for user in chat_users:
        user_calls = {
            'video': VideoCall.objects.filter(
                (Q(caller=request.user, receiver=user) | Q(caller=user, receiver=request.user))
            ).select_related('caller', 'receiver').order_by('-call_time')[:3],
            'voice': VoiceCall.objects.filter(
                (Q(caller=request.user, receiver=user) | Q(caller=user, receiver=request.user))
            ).select_related('caller', 'receiver').order_by('-call_time')[:3]
        }
        
        call_history[user.id] = {
            'video_calls': [{
                'id': call.id,
                'caller': call.caller.username,
                'receiver': call.receiver.username,
                'timestamp': call.call_time.strftime("%B %d, %I:%M %p"),
                'duration': str(call.duration) if call.duration else 'N/A',
                'is_outgoing': call.caller == request.user
            } for call in user_calls['video']],
            'voice_calls': [{
                'id': call.id,
                'caller': call.caller.username,
                'receiver': call.receiver.username,
                'timestamp': call.call_time.strftime("%B %d, %I:%M %p"),
                'duration': str(call.duration) if call.duration else 'N/A',
                'is_outgoing': call.caller == request.user
            } for call in user_calls['voice']]
        }
    
    context = {
        'chat_users': enhanced_users,
        'selected_user': selected_user,
        'messages': messages,
        'video_calls': video_calls,
        'voice_calls': voice_calls,
        'call_history': call_history,
        'selected_user_call_history': call_history.get(selected_user.id if selected_user else None, {})
    }
    
    return render(request, 'chats.html', context)

@login_required
def get_messages(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    messages = Message.objects.filter(
        (Q(sender=request.user, receiver=other_user) |
         Q(sender=other_user, receiver=request.user))
    ).order_by('timestamp')
    
    return JsonResponse({
        'messages': [{
            'content': msg.content,
            'sender': msg.sender.username,
            'timestamp': msg.timestamp.strftime("%I:%M %p"),
            'is_sent': msg.sender == request.user
        } for msg in messages]
    })

@login_required
def toggle_like(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        post_id = request.POST.get('post_id')
        post = get_object_or_404(UserPosts, id=post_id)
        
        like, created = PostLike.objects.get_or_create(user=request.user, post=post)
        
        if not created:
            like.delete()
            return JsonResponse({'status': 'unliked', 'count': post.post_likes.count()})
        
        return JsonResponse({'status': 'liked', 'count': post.post_likes.count()})
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def add_comment(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        post_id = data.get('post_id')
        content = data.get('content')
        
        try:
            post = UserPosts.objects.get(id=post_id)
            comment = PostComment.objects.create(
                user=request.user,
                post=post,
                content=content
            )
            
            # Update post's comment count
            post.total_comments = PostComment.objects.filter(post=post).count()
            post.save()
            
            # Create notification for comment
            if post.user != request.user:
                Notification.objects.create(
                    from_user=request.user,
                    to_user=post.user,
                    notification_type='post_comment',
                    related_post=post
                )
            
            return JsonResponse({
                'success': True,
                'username': request.user.username,
                'content': content,
                'created_at': comment.created_at.isoformat()
            })
        except UserPosts.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Post not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def get_comments(request, post_id):
    try:
        post = UserPosts.objects.get(id=post_id)
        comments = PostComment.objects.filter(post=post).order_by('-created_at')
        comments_data = [{
            'username': comment.user.username,
            'content': comment.content,
            'created_at': comment.created_at.isoformat()
        } for comment in comments]
        
        return JsonResponse({'comments': comments_data})
    except UserPosts.DoesNotExist:
        return JsonResponse({'comments': []})

# custom error pages handler

def error_404(request, exception):
    return render(request, 'errors/notfound-404.html', status=404)

def error_403(request, exception):
    return render(request, 'errors/forbidden-403.html', status=403)

@login_required
def like_post(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        post_id = data.get('post_id')
        post = get_object_or_404(UserPosts, id=post_id)
        
        like, created = PostLike.objects.get_or_create(user=request.user, post=post)
        
        if not created:
            like.delete()
            return JsonResponse({'status': 'unliked', 'likes': post.post_likes.count()})
        
        # Create notification for post like
        Notification.objects.create(
            from_user=request.user,
            to_user=post.user,
            notification_type='post_like',
            related_post=post
        )
        
        return JsonResponse({'status': 'liked', 'likes': post.post_likes.count()})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def add_comment(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        post_id = data.get('post_id')
        content = data.get('content')
        
        post = get_object_or_404(UserPosts, id=post_id)
        comment = PostComment.objects.create(
            user=request.user,
            post=post,
            content=content
        )
        
        # Create notification with comment content
        if post.user != request.user:
            Notification.notify_post_comment(
                from_user=request.user,
                to_user=post.user,
                post=post,
                comment_content=content
            )
        
        return JsonResponse({
            'status': 'success',
            'comment': {
                'username': request.user.username,
                'content': comment.content,
                'created_at': comment.created_at.strftime("%B %d, %Y %I:%M %p")
            }
        })
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def get_comments(request, post_id):
    post = get_object_or_404(UserPosts, id=post_id)
    comments = post.post_comments.select_related('user').order_by('-created_at')[:10]
    
    return JsonResponse({
        'comments': [{
            'id': comment.id,
            'username': comment.user.username,
            'content': comment.content,
            'created_at': comment.created_at.strftime("%B %d, %Y %I:%M %p"),
            'is_own_comment': comment.user == request.user
        } for comment in comments]
    })

@login_required
def share_post(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = json.loads(request.body)
        post_id = data.get('post_id')
        share_text = data.get('share_text', '')
        
        post = get_object_or_404(UserPosts, id=post_id)
        
        share, created = PostShare.objects.get_or_create(
            user=request.user,
            post=post,
            defaults={'share_text': share_text}
        )
        
        if not created:
            share.delete()
            return JsonResponse({
                'status': 'unshared',
                'count': post.post_shares.count()
            })
        
        return JsonResponse({
            'status': 'shared',
            'count': post.post_shares.count()
        })
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def repost_post(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = json.loads(request.body)
        post_id = data.get('post_id')
        repost_text = data.get('repost_text', '')
        
        post = get_object_or_404(UserPosts, id=post_id)
        
        try:
            repost, created = Repost.objects.get_or_create(
                user=request.user,
                original_post=post,
                defaults={'repost_text': repost_text}
            )
            
            if not created:
                repost.delete()
                return JsonResponse({
                    'status': 'unreposted',
                    'count': post.post_reposts.count()
                })
            
            return JsonResponse({
                'status': 'reposted',
                'count': post.post_reposts.count()
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def delete_comment(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = json.loads(request.body)
        comment_id = data.get('comment_id')
        
        try:
            comment = PostComment.objects.get(id=comment_id, user=request.user)
            comment.delete()
            return JsonResponse({'status': 'success'})
        except PostComment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Comment not found'}, status=404)
        
    return JsonResponse({'status': 'error'}, status=400)

@login_required(login_url='login')
def edit_profile(request):
    if request.method == 'POST':
        try:
            user = request.user
            # Access the UserProfile instance directly

            # Update User fields
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.email = request.POST.get('email')
            user.nickname = request.POST.get('nickname')
            user.user_bio = request.POST.get('bio')
            user.phone_number = request.POST.get('phone')
            user.user_place = request.POST.get('city')
            user.user_website = request.POST.get('website')
            user.gender = request.POST.get('gender')
            user.user_occupation = request.POST.get('occupation')
            user.user_education = request.POST.get('education')
            user.user_interests = request.POST.get('interests')
            
            # Handle date of birth
            date_of_birth = request.POST.get('date_of_birth')
            if date_of_birth:
                user.date_of_birth = date_of_birth
            
            # Handle profile picture
            if 'profile_picture' in request.FILES:
                user.profile_picture = request.FILES['profile_picture']
            
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_profile')
            
        except Exception as e:
            messages.error(request, f'Error updating profile: {str(e)}')
    
    return render(request, 'edit_profile.html', {'user': request.user})

@login_required
def upload_story(request):
    if request.method == 'POST':
        try:
            story_content = request.POST.get('story_content', '').strip()
            expires_at = timezone.now() + timedelta(hours=24)  # Stories expire after 24 hours
            
            image_url = None
            if 'story_image' in request.FILES:
                story_image = request.FILES['story_image']
                # Validate image type
                allowed_types = ['image/jpeg', 'image/png', 'image/gif']
                if story_image.content_type not in allowed_types:
                    return JsonResponse({'status': 'error', 'message': 'Invalid image type'})
                
                if story_image.size > 5 * 1024 * 1024:  # 5MB limit
                    return JsonResponse({'status': 'error', 'message': 'Image too large'})
                
                fs = FileSystemStorage()
                filename = fs.save(f'stories/{story_image.name}', story_image)
                image_url = fs.url(filename)
                if not image_url.startswith('/'):
                    image_url = '/' + image_url
            
            # Create story object
            story = UserStory.objects.create(
                user=request.user,
                story_content=story_content,
                story_image=image_url,
                expires_at=expires_at
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Story created successfully',
                'story_id': story.id,
                'image_url': image_url
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def get_stories(request):
    # Get stories from users that the current user follows
    following = UserFollowing.objects.filter(user=request.user).values_list('following_user', flat=True)
    
    # Get active stories that haven't expired
    active_stories = UserStory.objects.filter(
        Q(user__in=following) | Q(user=request.user),
        is_active=True,
        is_deleted=False,
        expires_at__gt=timezone.now()
    ).select_related('user').order_by('-created_at')
    
    stories_data = []
    for story in active_stories:
        stories_data.append({
            'id': story.id,
            'user': {
                'id': story.user.id,
                'username': story.user.username,
                'profile_picture': story.user.profile_picture.url if story.user.profile_picture else settings.DEFAULT_PROFILE_PIC
            },
            'content': story.story_content,
            'image': story.story_image.url if story.story_image else None,
            'created_at': story.created_at,
            'expires_at': story.expires_at,
            'views_count': story.story_count,
            'is_seen': story.is_seen,
            'is_own_story': story.user == request.user
        })
    
    return JsonResponse({'stories': stories_data})

@login_required
def view_story(request, story_id):
    story = get_object_or_404(UserStory, id=story_id, is_active=True, is_deleted=False)
    
    if request.method == 'POST':
        # Only increment view count if it's not the user's own story
        if story.user != request.user and not story.is_seen:
            story.mark_as_seen()
            story.increment_story_count()
    
    return JsonResponse({
        'status': 'success',
        'story': {
            'image': story.story_image.url if story.story_image else None,
            'content': story.story_content,
            'views_count': story.story_count,
            'username': story.user.username
        }
    })

@login_required
def initiate_call(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            receiver_id = data.get('receiver_id')
            call_type = data.get('call_type')
            
            if not receiver_id or not call_type:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Invalid request parameters'
                })
            
            receiver = get_object_or_404(User, id=receiver_id)
            
            # Check for existing active calls for either user
            active_call = VideoCall.objects.filter(
                (Q(caller=request.user) | Q(receiver=request.user) |
                 Q(caller=receiver) | Q(receiver=receiver)),
                status__in=['initiating', 'active']
            ).first()

            if active_call:
                other_user = active_call.receiver if active_call.caller == request.user else active_call.caller
                return JsonResponse({
                    'status': 'active_call',
                    'call': {
                        'id': active_call.id,
                        'type': 'video',
                        'other_user': {
                            'id': other_user.id,
                            'username': other_user.username,
                            'avatar': other_user.profile_picture.url if other_user.profile_picture else None
                        },
                        'start_time': active_call.call_time.isoformat(),
                        'status': active_call.status
                    }
                })

            # Create new call with proper status
            call = (VideoCall if call_type == 'video' else VoiceCall).objects.create(
                caller=request.user,
                receiver=receiver,
                status='initiating',
                call_time=timezone.now()
            )

            return JsonResponse({
                'status': 'success',
                'call': {
                    'id': call.id,
                    'type': call_type,
                    'receiver': {
                        'id': receiver.id,
                        'username': receiver.username,
                        'avatar': receiver.profile_picture.url if receiver.profile_picture else None
                    },
                    'start_time': call.call_time.isoformat(),
                    'status': 'initiating'
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Invalid request method'
    })

@login_required
def update_call_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            call_id = data.get('call_id')
            new_status = data.get('status')
            call_type = data.get('call_type', 'video')
            
            CallModel = VideoCall if call_type == 'video' else VoiceCall
            call = get_object_or_404(CallModel, id=call_id)
            
            if call.caller != request.user and call.receiver != request.user:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Unauthorized'
                })
            
            call.status = new_status
            call.save()
            
            return JsonResponse({
                'status': 'success',
                'call': {
                    'id': call.id,
                    'status': call.status,
                    'start_time': call.call_time.isoformat()
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
def get_active_call(request):
    try:
        # Check for any active calls where the user is either caller or receiver
        active_call = VideoCall.objects.filter(
            (Q(caller=request.user) | Q(receiver=request.user)),
            status__in=['initiating', 'active']
        ).select_related('caller', 'receiver').first()
        
        if not active_call:
            return JsonResponse({
                'status': 'success',
                'has_active_call': False
            })
        
        other_user = active_call.receiver if active_call.caller == request.user else active_call.caller
        
        return JsonResponse({
            'status': 'success',
            'has_active_call': True,
            'call': {
                'id': active_call.id,
                'type': 'video',  # or get from model if you have different types
                'status': active_call.status,
                'start_time': active_call.call_time.isoformat(),
                'other_user': {
                    'id': other_user.id,
                    'username': other_user.username,
                    'avatar': other_user.profile_picture.url if other_user.profile_picture else None
                }
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def end_call(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            call_id = data.get('call_id')
            call_type = data.get('call_type')
            duration = data.get('duration', 0)
            
            # Get the appropriate call model
            CallModel = VideoCall if call_type == 'video' else VoiceCall
            call = get_object_or_404(CallModel, id=call_id)
            
            if call.caller != request.user and call.receiver != request.user:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Unauthorized'
                })
            
            # Update call status and duration
            call.status = 'ended'
            call.duration = timedelta(milliseconds=int(duration)) if duration else None
            call.save()
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
def get_call_history(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    
    video_calls = VideoCall.objects.filter(
        Q(caller=request.user, receiver=other_user) |
        Q(caller=other_user, receiver=request.user)
    ).order_by('-call_time')[:5]
    
    voice_calls = VoiceCall.objects.filter(
        Q(caller=request.user, receiver=other_user) |
        Q(caller=other_user, receiver=request.user)
    ).order_by('-call_time')[:5]
    
    call_data = {
        'video_calls': [{
            'call_type': 'video',
            'caller_name': call.caller.username,
            'receiver_name': call.receiver.username,
            'timestamp': call.call_time.strftime("%B %d, %I:%M %p"),
            'duration': str(call.duration) if call.duration else 'N/A',
            'is_outgoing': call.caller == request.user
        } for call in video_calls],
        'voice_calls': [{
            'call_type': 'voice',
            'caller_name': call.caller.username,
            'receiver_name': call.receiver.username,
            'timestamp': call.call_time.strftime("%B %d, %I:%M %p"),
            'duration': str(call.duration) if call.duration else 'N/A',
            'is_outgoing': call.caller == request.user
        } for call in voice_calls]
    }
    
    return JsonResponse(call_data)


def rooms(request):
    category = request.GET.get('category', 'all')
    search_query = request.GET.get('search', '')
    
    rooms_query = Rooms.objects.filter(room_status='active')
    
    # Apply category filter
    if category != 'all':
        rooms_query = rooms_query.filter(room_category=category)
    
    # Apply search filter
    if search_query:
        rooms_query = rooms_query.filter(
            Q(room_name__icontains=search_query) |
            Q(room_description__icontains=search_query)
        )
    
    # Get featured rooms
    featured_rooms = rooms_query.filter(is_featured=True)
    
    # Get regular rooms
    regular_rooms = rooms_query.filter(is_featured=False)
    
    context = {
        'featured_rooms': featured_rooms,
        'rooms': regular_rooms,
        'current_category': category,
        'categories': dict(Rooms.CATEGORY_CHOICES),
        'search_query': search_query,
    }
    
    return render(request, 'rooms.html', context)

@login_required
def create_room(request):
    if request.method == 'POST':
        try:
            room = Rooms.objects.create(
                user=request.user,
                room_name=request.POST.get('room_name'),
                room_description=request.POST.get('room_description'),
                room_type=request.POST.get('room_type'),
                room_category=request.POST.get('room_category'),
            )
            
            if 'room_image' in request.FILES:
                room.room_image = request.FILES['room_image']
                room.save()
                
            messages.success(request, 'Room created successfully!')
            return redirect('rooms')
        except Exception as e:
            messages.error(request, f'Error creating room: {str(e)}')
            return redirect('rooms')
    
    return redirect('rooms')

@login_required
def join_room(request, room_id):
    room = get_object_or_404(Rooms, id=room_id)
    if room.join_room(request.user):
        # Get room messages
        room_messages = RoomMessage.objects.filter(room=room).select_related('user').order_by('timestamp')
        return render(request, 'room_detail.html', {
            'room': room,
            'room_messages': room_messages,
            'roomId': room_id  # Add room ID to context
        })
    return redirect('rooms')

@csrf_exempt  # Add this decorator
def room_messages(request, room_id):
    if request.method == 'POST':
        try:
            room = get_object_or_404(Rooms, id=room_id)
            data = json.loads(request.body)
            content = data.get('message', '').strip()
            
            if not content:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Message cannot be empty'
                }, status=400)
            
            message = RoomMessage.objects.create(
                room=room,
                user=request.user,
                content=content
            )
            
            # Return more detailed message data
            return JsonResponse({
                'status': 'success',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'username': message.user.username,
                    'timestamp': message.timestamp.strftime("%I:%M %p"),
                    'user_image': message.user.profile_picture.url if message.user.profile_picture else None,
                    'is_own_message': True
                }
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    # For GET requests, return recent messages
    room = get_object_or_404(Rooms, id=room_id)
    messages = RoomMessage.objects.filter(room=room).select_related('user').order_by('-timestamp')[:50]
    
    return JsonResponse({
        'messages': [{
            'id': msg.id,
            'content': msg.content,
            'username': msg.user.username,
            'timestamp': msg.timestamp.strftime("%I:%M %p"),
            'user_image': msg.user.profile_picture.url if msg.user.profile_picture else None,
            'is_own_message': msg.user == request.user
        } for msg in messages]
    })

@login_required
def leave_room(request, room_id):
    if request.method == 'POST':
        try:
            room = get_object_or_404(Rooms, id=room_id)
            
            # Remove user from room participants
            if request.user in room.participants.all():
                room.participants.remove(request.user)
                
                # If user is host and there are other participants, assign new host
                if request.user == room.user and room.participants.exists():
                    new_host = room.participants.first()
                    room.user = new_host
                    room.save()
                # If user is host and no other participants, delete room
                elif request.user == room.user:
                    room.delete()
                
                return JsonResponse({'status': 'success'})
            
            return JsonResponse({'status': 'error', 'message': 'User not in room'}, status=400)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def block_user(request):
    pass


def notifications(request):
    # Get notifications for the current user
    notifications = (
        Notification.objects.filter(
            Q(to_user=request.user) |
            Q(from_user=request.user, notification_type='follow_request_rejected')
        )
        .select_related('from_user', 'to_user')
        .order_by('-created_at')
    )

    # Mark unread notifications as read
    Notification.objects.filter(
        to_user=request.user,
        is_read=False
    ).update(is_read=True)

    # Group notifications by type
    grouped_notifications = {
        'follow_requests': [],
        'follow_accepts': [],
        'follow_backs': [],
        'rejected_requests': []
    }

    for notification in notifications:
        if notification.notification_type == 'follow_request':
            grouped_notifications['follow_requests'].append(notification)
        elif notification.notification_type == 'follow_accept':
            grouped_notifications['follow_accepts'].append(notification)
        elif notification.notification_type == 'follow_back':
            grouped_notifications['follow_backs'].append(notification)
        elif notification.notification_type == 'follow_request_rejected':
            grouped_notifications['rejected_requests'].append(notification)

    context = {
        'notifications': notifications,
        'grouped_notifications': grouped_notifications,
        'unread_count': notifications.filter(is_read=False).count()
    }
    
    return render(request, 'notification.html', context)

import datetime

import requests
import os

# Try to import geoip2, fallback to requests if not available
try:
    from geoip2.database import Reader
    GEOIP2_AVAILABLE = True
except ImportError:
    GEOIP2_AVAILABLE = False

# Path to the GeoLite2 database (update this path as needed)
GEOLITE2_DB_PATH = os.path.join(os.path.dirname(__file__), 'GeoLite2-City.mmdb')

def get_location_from_ip(ip):
    # For local development, override local/private IPs for testing
    if ip.startswith('127.') or ip.startswith('192.168.') or ip.startswith('10.') or ip == '::1':
        ip = '8.8.8.8'  # Google's public DNS for demo

    # Try geoip2 first if available and DB exists
    if GEOIP2_AVAILABLE and os.path.exists(GEOLITE2_DB_PATH):
        try:
            with Reader(GEOLITE2_DB_PATH) as reader:
                response = reader.city(ip)
                city = response.city.name or ''
                country = response.country.name or ''
                location = ', '.join(filter(None, [city, country]))
                return location if location else 'Location not found'
        except Exception:
            pass
    # Fallback to ipinfo.io
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=2)
        if response.status_code == 200:
            data = response.json()
            city = data.get('city', '')
            region = data.get('region', '')
            country = data.get('country', '')
            location = ', '.join(filter(None, [city, region, country]))
            return location if location else 'Location not found'
    except Exception:
        pass
    return 'Location not found'

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            request.session['password_error'] = True
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            request.session['password_error'] = True
        elif not new_password or len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters.')
            request.session['password_error'] = True
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)  # Prevent logout
            messages.success(request, 'Your password has been updated successfully!')
            request.session['password_error'] = False
        return redirect('settings')
    else:
        return redirect('settings')

@login_required
def settings(request):
    # Get user IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')

    # Get device info from user agent
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown Device')
    device = user_agent[:50]  # Truncate for display

    # Get location using ipinfo.io
    location = get_location_from_ip(ip)

    # Get current time
    now = datetime.datetime.now()

    # Example: List of login activity (current session only for now)
    login_activity = [
        {
            'device': device,
            'location': location,
            'ip': ip,
            'time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'current': True,
        },
        # Add more sessions here if you implement session tracking
    ]

    # Check if there was a password error (to keep accordion open)
    password_error = request.session.pop('password_error', None)
    username_error = request.session.pop('username_error', None)

    if request.method == 'POST':
        new_username = request.POST.get('new_username')
        if new_username is not None:
            # Username change logic
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not new_username.strip():
                messages.error(request, 'Username cannot be empty.')
                request.session['username_error'] = True
            elif len(new_username) < 3 or len(new_username) > 30:
                messages.error(request, 'Username must be between 3 and 30 characters.')
                request.session['username_error'] = True
            elif not new_username.isalnum():
                messages.error(request, 'Username must be alphanumeric.')
                request.session['username_error'] = True
            elif User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                messages.error(request, 'This username is already taken.')
                request.session['username_error'] = True
            else:
                request.user.username = new_username
                request.user.save()
                messages.success(request, 'Your username has been updated successfully!')
                request.session['username_error'] = False
            return redirect('settings')

    context = {
        'login_activity': login_activity,
        'password_error': password_error,
        'username_error': username_error,
    }
    return render(request, 'settings.html', context)