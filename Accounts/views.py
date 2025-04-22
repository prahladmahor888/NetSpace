from django.contrib.auth import logout as auth_logout
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.contrib.auth import login as auth_login
from django.core.cache import cache
from Accounts.models import CustomUser as User
from django.utils import timezone
from datetime import timedelta
import json
import re
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from .models import BlockUser
from django.db.models import Q

# Create your views here.

@require_http_methods(['POST'])
def check_username(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        
        if not username:
            return JsonResponse({'error': 'Username is required'}, status=400)
            
        # Validate username format
        pattern = re.compile(r'^[A-Za-z][A-Za-z0-9_]{2,19}$')
        if not pattern.match(username):
            return JsonResponse({
                'error': 'Username must start with a letter and contain 3-20 characters (letters, numbers, underscores)',
                'available': False
            }, status=400)
            
        # Check if username exists
        User = get_user_model()
        username_exists = User.objects.filter(username=username).exists()
        
        if username_exists:
            # Generate suggestions
            suggestions = []
            # Try adding numbers
            for i in range(1, 5):
                suggestion = f"{username}{i}"
                if not User.objects.filter(username=suggestion).exists():
                    suggestions.append(suggestion)
            # Try adding underscores
            suggestion = f"{username}_"
            if not User.objects.filter(username=suggestion).exists():
                suggestions.append(suggestion)
            
            return JsonResponse({
                'available': False,
                'suggestions': suggestions[:3]  # Return up to 3 suggestions
            })
        
        return JsonResponse({'available': True})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me') == 'on'

        # Check for rate limiting
        ip_address = request.META.get('REMOTE_ADDR')
        cache_key = f'login_attempts_{ip_address}'
        login_attempts = cache.get(cache_key, 0)

        if login_attempts >= 5:  # Max 5 attempts
            return render(request, 'auth/login.html', {
                'error': 'Too many login attempts. Please try again later.'
            })

        # Validate required fields
        if not username or not password:
            return render(request, 'auth/login.html', {
                'error': 'Username and password are required'
            })

        # Get user and verify credentials
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                # Reset login attempts on successful login
                cache.delete(cache_key)
                
                # Login user and set session
                auth_login(request, user)
                
                # Set session expiry based on remember me
                if remember_me:
                    request.session.set_expiry(timedelta(days=14))  # 2 weeks
                else:
                    request.session.set_expiry(0)  # Until browser closes
                
                # Update last login
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                                              
                return redirect('home')
            else:
                # Increment login attempts
                cache.set(cache_key, login_attempts + 1, 300)  # 5 minutes timeout
                return render(request, 'auth/login.html', {'error': 'Invalid credentials'})
        except User.DoesNotExist:
            # Increment login attempts
            cache.set(cache_key, login_attempts + 1, 300)  # 5 minutes timeout
            return render(request, 'auth/login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'auth/login.html')


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        gender = request.POST.get('gender', '').strip()
        password = request.POST.get('password', '')

        # Validate required fields
        if not all([username, email, phone, gender, password]):
            return render(request, 'auth/register.html', {'error': 'All fields are required'})

        # Validate username format and length
        if not re.match(r'^[A-Za-z0-9_]{3,20}$', username):
            return render(request, 'auth/register.html', {'error': 'Username must be 3-20 characters and can only contain letters, numbers, and underscores'})

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return render(request, 'auth/register.html', {'error': 'Username already taken'})

        # Validate email format
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return render(request, 'auth/register.html', {'error': 'Please enter a valid email address'})

        # Check if email already exists
        if User.objects.filter(email=email).exists():    
            return render(request, 'auth/register.html', {'error': 'Email already registered'})

        # Validate phone number format
        if not re.match(r'^[0-9]{10}$', phone):
            return render(request, 'auth/register.html', {'error': 'Please enter a valid 10-digit phone number'})

        # Check if phone number already exists
        if User.objects.filter(phone_number=phone).exists():
            return render(request, 'auth/register.html', {'error': 'Phone number already registered'})

        # Validate password strength
        if not re.match(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z]).{8,}$', password):
            return render(request, 'auth/register.html', {'error': 'Password must be at least 8 characters long, contain an uppercase letter, a lowercase letter, and a digit'})

        # Validate gender
        if gender.lower() not in ['male', 'female', 'other']:
            return render(request, 'auth/register.html', {'error': 'Please select a valid gender'})

        try:

            # Create user with validated data
            user = User.objects.create_user(
                username=username,
                email=email,
                phone=phone,
                gender=gender.capitalize(),
                password=password,
            )
            user.save()

            # Redirect to login page with success message
            return render(request, 'auth/login.html', {'success': 'Registration successful! Please login.'})
                
        except Exception as e:
            return render(request, 'auth/register.html', {'error': 'An error occurred during registration. Please try again.'})

    return render(request, 'auth/register.html')

def logout(request):
    # Get the response object for redirection before logout
    response = redirect('login')
    
    # Clear all session data and perform Django's built-in logout
    request.session.flush()
    auth_logout(request)
    
    # Delete all cookies that might contain sensitive information
    for key in request.COOKIES:
        response.delete_cookie(key)
    
    # Set security headers
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


# custom error pages handler

def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)

def handler403(request, exception):
    return render(request, 'errors/403.html', status=403)

@login_required
@require_http_methods(['POST'])
def block_user(request):
    try:
        data = json.loads(request.body)
        blocked_user_id = data.get('user_id')
        block_type = data.get('block_type', 'other')
        reason = data.get('reason', '')
        duration_days = data.get('duration')  # in days, None for permanent

        if not blocked_user_id:
            return JsonResponse({'error': 'User ID is required'}, status=400)

        blocked_user = get_object_or_404(User, id=blocked_user_id)
        
        # Check if already blocked
        if BlockUser.objects.is_blocked(request.user, blocked_user):
            return JsonResponse({'error': 'User is already blocked'}, status=400)

        block_duration = timedelta(days=duration_days) if duration_days else None
        
        block = BlockUser.objects.create(
            user=request.user,
            blocked_user=blocked_user,
            block_type=block_type,
            reason=reason,
            block_duration=block_duration,
            is_permanent=block_duration is None
        )

        return JsonResponse({
            'message': 'User blocked successfully',
            'block_id': block.id
        })

    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(['POST'])
def unblock_user(request):
    try:
        data = json.loads(request.body)
        blocked_user_id = data.get('user_id')
        reason = data.get('reason', '')

        if not blocked_user_id:
            return JsonResponse({'error': 'User ID is required'}, status=400)

        blocked_user = get_object_or_404(User, id=blocked_user_id)
        block = BlockUser.objects.get(
            user=request.user,
            blocked_user=blocked_user,
            status='active'
        )
        
        block.unblock(reason=reason)
        return JsonResponse({'message': 'User unblocked successfully'})

    except BlockUser.DoesNotExist:
        return JsonResponse({'error': 'Block not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(['GET'])
def get_blocked_users(request):
    try:
        blocks = BlockUser.objects.get_user_blocks(request.user)
        blocked_users = [{
            'id': block.blocked_user.id,
            'username': block.blocked_user.username,
            'block_type': block.block_type,
            'created_at': block.created_at,
            'is_permanent': block.is_permanent,
            'expires_at': (block.created_at + block.block_duration) if block.block_duration else None
        } for block in blocks]

        return JsonResponse({'blocked_users': blocked_users})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def block_user_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            blocked_user_id = data.get('user_id')
            block_type = data.get('block_type', 'other')
            reason = data.get('reason', '')
            duration = data.get('duration')  # in days, None for permanent
            
            blocked_user = get_object_or_404(User, id=blocked_user_id)
            
            # Check if already blocked
            if BlockUser.objects.is_blocked(request.user, blocked_user):
                return JsonResponse({'error': 'User is already blocked'}, status=400)
            
            # Create block
            block_duration = timedelta(days=duration) if duration else None
            block = BlockUser.objects.create(
                user=request.user,
                blocked_user=blocked_user,
                block_type=block_type,
                reason=reason,
                block_duration=block_duration,
                is_permanent=block_duration is None
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'User blocked successfully'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def unblock_user_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            reason = data.get('reason', '')
            
            block = get_object_or_404(
                BlockUser, 
                user=request.user, 
                blocked_user_id=user_id, 
                status='active'
            )
            block.unblock(reason=reason)
            
            return JsonResponse({'status': 'success', 'message': 'User unblocked successfully'})
        except BlockUser.DoesNotExist:
            return JsonResponse({'error': 'Block not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def user_chats(request):
    try:
        # Get all users except the current user
        chat_users = User.objects.exclude(id=request.user.id)
        
        # Get blocked users (both blocked by and blocking current user)
        blocked_users = BlockUser.objects.filter(
            Q(user=request.user, status='active') |
            Q(blocked_user=request.user, status='active')
        )
        
        blocked_ids = set(blocked_users.values_list('blocked_user', flat=True))
        blocking_ids = set(blocked_users.values_list('user', flat=True))
        
        # Add is_blocked flag to users
        for user in chat_users:
            user.is_blocked = user.id in blocked_ids or user.id in blocking_ids
        
        return render(request, 'chats.html', {
            'chat_users': chat_users,
        })
    except Exception as e:
        return render(request, 'errors/500.html', {'error': str(e)})