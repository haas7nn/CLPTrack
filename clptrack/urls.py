"""Which address opens which page.

/admin/     the back office that comes with Django
/accounts/  sign in and sign out, also from Django
/           our own pages, listed in dashboard/urls.py
"""
from django.contrib import admin
from django.urls import include, path

from accounts.views import ChangePassword, ResetConfirm

# the back office carries our name instead of the default one
admin.site.site_header = "CLPTrack admin"
admin.site.site_title = "CLPTrack"
admin.site.index_title = "People, deadlines and records"

urlpatterns = [
    path("admin/", admin.site.urls),
    # our two versions first, so they are used instead of the built in ones with the same address
    path("accounts/password_change/", ChangePassword.as_view(), name="password_change"),
    path("accounts/reset/<uidb64>/<token>/", ResetConfirm.as_view(), name="password_reset_confirm"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("dashboard.urls")),
    path("", include("progress.urls")),
    path("", include("risk.urls")),
]

