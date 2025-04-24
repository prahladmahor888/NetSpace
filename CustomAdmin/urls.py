from django.contrib import admin
from django.urls import path, include
from CustomAdmin import views
from django.conf.urls.static import static
from django.conf import settings
from CustomAdmin.user_management import add_user, update_user

urlpatterns = [
    
    path('comments-count/', views.comments_count_api, name='comments_count_api'),
    
    path('', views.admin_login, name='admin_login'),
    path('deshboard/', views.dashboard, name='dashboard'),
    path('admin_users/', views.admin_users, name="admin_users"),
    path('add-user/', add_user, name='add_user'),
    path('update-user/<int:user_id>/', update_user, name='update_user'),
    path('admin_users/edit/<int:id>/', views.admin_edit_user, name='admin_edit_user'),
    path('admin_forms/', views.admin_users_form, name="admin_forms"),
    path('users/', views.admin_users_list, name='admin_users_list'),
    path('users/add/', views.admin_add_user_form, name='admin_add_user_form'),
    path('users/add/submit/', views.admin_add_user, name='admin_add_user'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)