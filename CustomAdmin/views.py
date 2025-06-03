import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import render, redirect, get_object_or_404
from Accounts.models import CustomUser as User
from django.contrib.auth import login, authenticate, logout as auth_logout
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils.timezone import make_aware
from datetime import datetime
from django.contrib.auth.decorators import login_required, user_passes_test

User = get_user_model()

# Real-time API models
from NetSpace.models import PostComment, UserPosts
from .models import Visitor
from django.contrib.sessions.models import Session
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

def comments_count_api(request):
    count = PostComment.objects.count()
    return JsonResponse({'total_comments': count})

def visitor_stats_api(request):
    """API endpoint for real-time visitor statistics and posts count"""
    return JsonResponse({
        'total_visitors': Visitor.total_count(),
        'total_posts': UserPosts.objects.count()
    })

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def record_visitor_api(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body.decode('utf-8'))
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = data.get('user_agent', '')[:255]
        referrer = data.get('referrer', '')
        session_key = data.get('session_key', '')
        user_id = data.get('user_id')
        user = User.objects.filter(id=user_id).first() if user_id else None
        query = {'ip_address': ip_address}
        if user:
            query['user'] = user

        if not Visitor.objects.filter(**query).exists():
            Visitor.objects.create(
                ip_address=ip_address,
                user_agent=user_agent,
                referrer=referrer,
                session_key=session_key,
                user=user
            )
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid'}, status=400)

def admin_login(request):
    try:
        # If user is already authenticated
        if request.user.is_authenticated:
            if request.user.is_superuser or request.user.is_staff:
                return redirect('dashboard')
            else:
                # If normal user is logged in, log them out
                auth_logout(request)
                messages.info(request, 'You have been logged out. Please login with admin credentials.')
                return render(request, 'admin-login.html', {'error': 'Only admin and staff members are allowed.'})
        
        if request.method == 'POST':
            ip_address = request.META.get('REMOTE_ADDR')
            cache_key = f'admin_login_attempts_{ip_address}'
            login_attempts = cache.get(cache_key, 0)

            if login_attempts >= 5:
                messages.error(request, 'Too many login attempts. Please try again later.')
                return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

            username = request.POST.get('username')
            password = request.POST.get('password')
            
            # First check if user exists
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                messages.error(request, 'Username does not exist')
                cache.set(cache_key, login_attempts + 1, 300)
                return render(request, 'admin-login.html')

            # Try to authenticate user
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Check if user is admin or staff
                if user.is_superuser or user.is_staff:
                    login(request, user)
                    cache.delete(cache_key)  # Reset login attempts on success
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Only admin and staff members are allowed.')
            else:
                messages.error(request, 'Invalid credentials.')
            
            # Increment login attempts on any failure
            cache.set(cache_key, login_attempts + 1, 300)
            return render(request, 'admin-login.html')
            
        return render(request, 'admin-login.html')
    
    except Exception as e:
        return render(request, 'admin-login.html', {'error': str(e)})

def admin_logout(request):
    """Logs out the user and redirects to the login page."""
    auth_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('admin_login')

def is_admin_or_staff(user):
    return user.is_superuser or user.is_staff

@login_required
@user_passes_test(is_admin_or_staff, login_url='admin_login')
def dashboard(request):
    # Additional check for admin/staff status
    if not request.user.is_superuser and not request.user.is_staff:
        return redirect('admin_login')

    # Get date 7 days ago
    seven_days_ago = timezone.now() - timedelta(days=7)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Get user statistics
    total_users = User.objects.count()
    new_users_count = User.objects.filter(date_joined__gte=seven_days_ago).count()
    
    # Get visitor statistics and post count
    visitor_stats = {
        'total_visitors': Visitor.total_count()
    }
    total_posts = UserPosts.objects.count()
    
    # Calculate percentage increase
    past_users = User.objects.filter(date_joined__gte=thirty_days_ago, date_joined__lt=seven_days_ago).count()
    if past_users > 0:
        percentage_increase = ((new_users_count - past_users) / past_users) * 100
    else:
        percentage_increase = 100 if new_users_count > 0 else 0

    # Get new users in last 7 days for the list
    new_users = User.objects.filter(
        date_joined__gte=seven_days_ago
    ).order_by('-date_joined').values(
        'username', 'email', 'date_joined'
    )

    users_data = [{
        'name': user['username'],
        'email': user['email'],
        'date': user['date_joined']
    } for user in new_users]

    # Get user activity for the last 6 months
    today = timezone.now()
    months_data = []
    labels = []
    
    for i in range(5, -1, -1):
        month_start = today - timedelta(days=today.day-1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        count = User.objects.filter(date_joined__range=(month_start, month_end)).count()
        months_data.append(count)
        labels.append(month_start.strftime('%b'))

    # Calculate user distribution
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()
    new_users = User.objects.filter(date_joined__gte=seven_days_ago).count()
    # premium_users = User.objects.filter(is_premium=True).count()  # Add this field to your User model if needed

    user_distribution = {
        'labels': ['Active Users', 'Inactive Users', 'New Users'],
        'data': [active_users, inactive_users, new_users]
    }

    context = {
        'new_users': users_data,
        'total_users': total_users,
        'new_users_count': new_users_count,
        'percentage_increase': round(percentage_increase, 1),
        'activity_labels': json.dumps(labels),
        'activity_data': json.dumps(months_data),
        'user_distribution': {
            'labels': json.dumps(['Active Users', 'Inactive Users', 'New Users']),
            'data': json.dumps([active_users, inactive_users, new_users])
        },
        'visitor_stats': visitor_stats,
        'total_posts': total_posts
    }
    
    return render(request, 'dashboard.html', context)

def admin_users(request):
    return admin_users_view(request)  # Use the complete view function

@csrf_protect
def toggle_users_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_ids = data.get('user_ids', [])
            users = User.objects.filter(id__in=user_ids)
            for user in users:
                user.is_active = not user.is_active
                user.save()
            return JsonResponse({'status': 'success', 'updated_count': len(users)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@csrf_exempt
def record_visitor_api(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body.decode('utf-8'))
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = data.get('user_agent', '')[:255]
        referrer = data.get('referrer', '')
        session_key = data.get('session_key', '')
        user_id = data.get('user_id')
        user = User.objects.filter(id=user_id).first() if user_id else None

        Visitor.objects.create(
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            session_key=session_key,
            user=user
        )
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid'}, status=400)

def admin_users_view(request):
    User = get_user_model()
    users = User.objects.all()
    admin_users = User.objects.filter(is_staff=True)
    
    context = {
        'users': users,
        'admin_users_count': admin_users.count(),
        'admin_users': admin_users,
        'active_users_count': users.filter(is_active=True).count(),
        'new_users_count': users.filter(date_joined__gte=timezone.now() - timezone.timedelta(days=7)).count(),
        'premium_users_count': users.filter(is_premium=True).count() if hasattr(User, 'is_premium') else 0,
    }
    return render(request, 'admin-users.html', context)

def admin_users_form(request):
    return render(request, '/adminforms/users-form.html')

def admin_users_list(request):
    # Add your logic to fetch users
    return render(request, 'admin-users.html')

def admin_add_user_form(request):
    return render(request, 'adminforms/user-form.html')

def admin_add_user(request):
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.POST.get('firstName')
            last_name = request.POST.get('lastName')
            email = request.POST.get('email')
            username = request.POST.get('username')
            password = request.POST.get('password')
            phone = request.POST.get('phone')
            dob = request.POST.get('dob')
            gender = request.POST.get('gender')
            status = request.POST.get('status')
            joining_date = request.POST.get('joining_date')
            user_roles = request.POST.getlist('user_role')

            # Validate if username exists
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Username already exists'
                })

            # Validate if email exists
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Email already exists'
                })

            # Create new user with basic fields first
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=status == 'active',
                date_joined=make_aware(datetime.strptime(joining_date, '%Y-%m-%dT%H:%M')) if joining_date else timezone.now(),
            )

            # Set password separately
            user.set_password(password)

            # Set additional fields if they exist in your model
            if hasattr(User, 'phone_number'):
                user.phone_number = phone
            if hasattr(User, 'date_of_birth'):
                user.date_of_birth = dob
            if hasattr(User, 'gender'):
                user.gender = gender
            if hasattr(User, 'user_bio'):
                user.uaer_bio = request.POST.get('bio')
            if hasattr(User, 'email_notifications'):
                user.email_notifications = request.POST.get('emailNotifications') == 'on'

            # Handle user roles
            if 'superuser' in user_roles:
                user.is_superuser = True
                user.is_staff = True
            elif 'staff' in user_roles:
                user.is_staff = True

            user.save()

            # Handle profile picture
            if 'profilePicture' in request.FILES:
                profile_pic = request.FILES['profilePicture']
                if hasattr(User, 'profile_picture'):
                    user.profile_picture = profile_pic
                    user.save()

            return JsonResponse({
                'success': True,
                'message': 'User created successfully'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })

    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_edit_user(request, id):  # Changed from user_id to id
    user = get_object_or_404(User, id=id)
    
    if request.method == 'GET':
        # Prepare user data
        user_data = {
            'id': str(id),  # Convert id to string to ensure proper serialization
            'firstName': user.first_name,
            'lastName': user.last_name,
            'email': user.email,
            'username': user.username,
            'phone': user.phone_number if hasattr(user, 'phone_number') else '',
            'dob': user.date_of_birth.strftime('%Y-%m-%d') if hasattr(user, 'date_of_birth') and user.date_of_birth else '',
            'gender': user.gender if hasattr(user, 'gender') else '',
            'bio': user.user_bio if hasattr(user, 'user_bio') else '',
            'status': 'active' if user.is_active else 'inactive',
            'user_roles': [],
            'emailNotifications': user.email_notifications if hasattr(user, 'email_notifications') else False,
            'joining_date': user.date_joined.strftime('%Y-%m-%dT%H:%M') if user.date_joined else '',
            'last_login': user.last_login.strftime('%Y-%m-%dT%H:%M') if user.last_login else '',
            'update_date': user.updated_at.strftime('%Y-%m-%dT%H:%M') if hasattr(user, 'updated_at') and user.updated_at else '',
        }

        # Add user roles
        if user.is_superuser:
            user_data['user_roles'].append('superuser')
        if user.is_staff:
            user_data['user_roles'].append('staff')
        if not user.is_superuser and not user.is_staff:
            user_data['user_roles'].append('normal')

        # Add profile picture URL if exists
        if hasattr(user, 'profile') and user.profile.profile_picture:
            user_data['profilePicture'] = user.profile.profile_picture.url

        return render(request, 'adminforms/user-form.html', {'user_data': json.dumps(user_data, default=str)})
    
    if request.method == 'POST':
        try:
            data = request.POST.copy()
            file_data = request.FILES

            # Handle user data updates
            user.first_name = data.get('firstName', user.first_name)
            user.last_name = data.get('lastName', user.last_name)
            user.email = data.get('email', user.email)
            
            # Only update password if provided
            password = data.get('password')
            if password:
                user.set_password(password)

            # Handle profile picture
            if 'profilePicture' in file_data:
                user.profile_picture = file_data['profilePicture']

            # Update other profile fields
            user.phone_number = data.get('phone', user.phone_number)
            user.date_of_birth = data.get('dob', user.date_of_birth)
            user.gender = data.get('gender', user.gender)
            user.user_bio = data.get('bio', user.uaer_bio)
            
            # Handle user roles
            user.is_superuser = 'superuser' in data.getlist('user_role', [])
            user.is_staff = 'staff' in data.getlist('user_role', [])
            
            # Handle status
            user.is_active = data.get('status') == 'active'

            user.save()
            user.profile.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    # Prepare user data for the template
    user_data = {
        'id': user.id,
        'firstName': user.first_name,
        'lastName': user.last_name,
        'email': user.email,
        'username': user.username,
        'phone': user.phone_number if hasattr(user, 'phone_number') else '',
        'dob': user.date_of_birth.strftime('%Y-%m-%d') if hasattr(user, 'date_of_birth') and user.date_of_birth else '',
        'gender': user.gender if hasattr(user, 'gender') else '',
        'bio': user.user_bio if hasattr(user, 'user_bio') else '',
        'status': 'active' if user.is_active else 'inactive',
        'user_roles': [],
        'last_login': user.last_login.isoformat() if user.last_login else '',
        'joining_date': user.date_joined.isoformat() if user.date_joined else '',
        'update_date': user.updated_at.isoformat() if hasattr(user, 'updated_at') and user.profile.updated_at else '',
        'emailNotifications': user.email_notifications if hasattr(user, 'email_notifications') else False,
    }

    # Add user roles
    if user.is_superuser:
        user_data['user_roles'].append('superuser')
    if user.is_staff:
        user_data['user_roles'].append('staff')
    if not user.is_superuser and not user.is_staff:
        user_data['user_roles'].append('normal')

    # Add profile picture URL if exists
    if hasattr(user, 'profile_picture') and user.profile_picture:
        user_data['profilePicture'] = user.profile_picture.url

    return render(request, 'adminforms/user-form.html', {'user_data': user_data})