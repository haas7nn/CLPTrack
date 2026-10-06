from django.urls import path

from . import views

urlpatterns = [
    path("deliverables/<int:deliverable_id>/submit/", views.submit, name="submit"),
    path("meetings/", views.meetings, name="meetings"),
    path("actions/<int:action_id>/done/", views.action_done, name="action_done"),
    path("students/<int:student_id>/", views.student_detail, name="student_detail"),
]
