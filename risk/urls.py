from django.urls import path

from . import views

urlpatterns = [
    path("tasks/daily/", views.run_daily, name="run_daily"),
]
