from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = 'مدیریت کشت‌تامین'
admin.site.site_title = 'کشت‌تامین'
admin.site.index_title = 'طرح‌ها و سرمایه‌گذاران'

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('portal.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

handler404 = 'portal.views.public.page_not_found'
