"""Pages for handing in work, recording meetings and leaving feedback."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from dashboard.views import role_required, timeline_for
from .forms import FeedbackForm, MeetingForm, SubmissionForm
from .models import Action, Deliverable, Meeting, Submission


@role_required("student")
def submit(request, deliverable_id):
    """A student uploads a file for one deliverable."""
    deliverable = get_object_or_404(Deliverable, pk=deliverable_id)
    form = SubmissionForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        f = form.cleaned_data["file"]
        Submission.objects.create(
            student=request.user, deliverable=deliverable,
            filename=f.name, content_type=f.content_type or "application/octet-stream",
            size=f.size, data=f.read(), note=form.cleaned_data["note"],
        )
        messages.success(request, f"Your file for {deliverable.title} was uploaded.")
        return redirect("student_home")
    return render(request, "progress/submit.html", {"form": form, "deliverable": deliverable})


@role_required("student")
def meetings(request):
    """A student sees their meetings and records a new one."""
    form = MeetingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        meeting = form.save(commit=False)
        meeting.student = request.user
        meeting.save()
        for line in form.action_lines():
            Action.objects.create(meeting=meeting, description=line)
        messages.success(request, "Your meeting was recorded.")
        return redirect("meetings")
    my_meetings = request.user.meetings.prefetch_related("actions")
    return render(request, "progress/meetings.html", {"form": form, "meetings": my_meetings})


@role_required("student")
@require_POST
def action_done(request, action_id):
    """A student ticks one of their own agreed actions as done."""
    action = get_object_or_404(Action, pk=action_id, meeting__student=request.user)
    action.done = True
    action.done_at = timezone.now()
    action.save()
    return redirect("meetings")


@role_required("supervisor")
def student_detail(request, student_id):
    """A supervisor looks at one of their students and can leave feedback."""
    student = get_object_or_404(User, pk=student_id, role="student", supervisor=request.user)
    form = FeedbackForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        feedback = form.save(commit=False)
        feedback.supervisor = request.user
        feedback.student = student
        feedback.save()
        messages.success(request, "Your feedback was saved.")
        return redirect("student_detail", student_id=student.id)
    history = list(student.risk_scores.order_by("scored_on").values("scored_on", "score"))
    return render(request, "progress/student_detail.html", {
        "student": student,
        "rows": timeline_for(student),
        "meetings": student.meetings.prefetch_related("actions"),
        "feedback": student.feedback_received.all(),
        "risk": student.risk_scores.first(),
        "form": form,
        # the chart needs plain lists, one of dates and one of scores
        "chart": {"labels": [h["scored_on"].strftime("%d %b") for h in history], "scores": [h["score"] for h in history]},
    })


@login_required
def download(request, submission_id):
    """Sends a submitted file back. Only the student, their supervisor or the coordinator may open it."""
    submission = get_object_or_404(Submission.objects.select_related("student"), pk=submission_id)
    user = request.user
    allowed = (user == submission.student or user == submission.student.supervisor or user.is_coordinator)
    if not allowed:
        raise PermissionDenied
    response = HttpResponse(bytes(submission.data), content_type=submission.content_type or "application/octet-stream")
    response["Content-Disposition"] = f'attachment; filename="{submission.filename}"'
    return response
