from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('kiberclub/', include('app_kiberclub.urls')),
    path('accounts/', include('app_accounts.urls')),
    path('admin_management/', include('app_admin_management.urls')),
    path('kibershop/', include('app_kibershop.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)