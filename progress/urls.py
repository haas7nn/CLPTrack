from django.urls import path

from . import views

urlpatterns = [
    path("submissions/<int:submission_id>/download/", views.download, name="download"),
    path("deliverables/<int:deliverable_id>/submit/", views.submit, name="submit"),
    path("meetings/", views.meetings, name="meetings"),
    path("actions/<int:action_id>/done/", views.action_done, name="action_done"),
    path("feedback/<int:feedback_id>/addressed/", views.feedback_addressed, name="feedback_addressed"),
    path("meetings/<int:meeting_id>/review/", views.meeting_review, name="meeting_review"),
    path("students/<int:student_id>/", views.student_detail, name="student_detail"),
    path("students/<int:student_id>/report/", views.student_report, name="student_report"),
]
