from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None
    return dictionary.get(str(key))

@register.filter
def get_profile_pic(user):
    if user is None:
        return '/static/images/default-pfp.png'
    return user.profile_picture.url if hasattr(user, 'profile_picture') and user.profile_picture else '/static/images/default-pfp.png'

@register.filter
def get_username(user):
    if user is None:
        return ''
    return user.username

@register.filter
def get_user_id(user):
    if user is None:
        return ''
    return user.id
