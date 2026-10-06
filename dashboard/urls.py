from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("student/", views.student_home, name="student_home"),
    path("supervisor/", views.supervisor_home, name="supervisor_home"),
    path("coordinator/", views.coordinator_home, name="coordinator_home"),
]
