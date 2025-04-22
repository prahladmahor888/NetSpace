from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import json

@login_required
@require_http_methods(["POST"])
def add_user(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        is_active = data.get('is_active', True)

        if not username or not email or not password:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})

        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Username already exists'})

        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already exists'})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=is_active
        )

        return JsonResponse({'success': True, 'user_id': user.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def update_user(request, user_id):
    try:
        data = json.loads(request.body)
        user = User.objects.get(id=user_id)

        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        is_active = data.get('is_active')

        if username and username != user.username:
            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'error': 'Username already exists'})
            user.username = username

        if email and email != user.email:
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'Email already exists'})
            user.email = email

        if password:
            user.set_password(password)

        if is_active is not None:
            user.is_active = is_active

        user.save()
        return JsonResponse({'success': True})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})