"""Which address opens which page.

/admin/     the back office that comes with Django
/accounts/  sign in and sign out, also from Django
/           our own pages, listed in dashboard/urls.py
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("dashboard.urls")),
]

if settings.DEBUG:
    # lets the dev server show uploaded files, the real host does this itself
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
