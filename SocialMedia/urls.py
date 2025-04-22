from django.contrib import admin
from django.urls import path, include
from Accounts import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Accounts.urls')),
    path('customadmin/', include('CustomAdmin.urls')),
    path('netspace/', include('NetSpace.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'Accounts.views.handler404'
# handler500 = 'NetSpace.views.handler500'
handler403 = 'Accounts.views.handler403'