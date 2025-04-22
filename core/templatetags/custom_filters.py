from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_profile_pic(user):
    return user.profile_picture.url if hasattr(user, 'profile_picture') and user.profile_picture else '/static/images/default-pfp.png'

@register.filter
def get_username(user):
    return user.username

@register.filter
def get_user_id(user):
    return user.id
