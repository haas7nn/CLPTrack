"""Which address opens which page.

/admin/     the back office that comes with Django
/accounts/  sign in and sign out, also from Django
/           our own pages, listed in dashboard/urls.py
"""
from django.contrib import admin
from django.urls import include, path

# the back office carries our name instead of the default one
admin.site.site_header = "CLPTrack admin"
admin.site.site_title = "CLPTrack"
admin.site.index_title = "People, deadlines and records"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("dashboard.urls")),
    path("", include("progress.urls")),
    path("", include("risk.urls")),
]

