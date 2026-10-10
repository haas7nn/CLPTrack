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
from .models import Action, Deliverable, Submission


@role_required("student")
def submit(request, deliverable_id):
    """A student uploads a file for one deliverable.

    Uploading again replaces the file and the note. The time of the first upload is kept, because
    lateness is about when the work first arrived, and a corrected version should not count against you.
    """
    deliverable = get_object_or_404(Deliverable, pk=deliverable_id)
    existing = Submission.objects.filter(student=request.user, deliverable=deliverable).first()
    form = SubmissionForm(request.POST or None, request.FILES or None, initial={"note": existing.note if existing else ""})
    if request.method == "POST" and form.is_valid():
        f = form.cleaned_data["file"]
        details = dict(filename=f.name, content_type=f.content_type or "application/octet-stream",
                       size=f.size, data=f.read(), note=form.cleaned_data["note"])
        if existing:
            for field, value in details.items():
                setattr(existing, field, value)
            existing.save()
            messages.success(request, f"Your file for {deliverable.title} was replaced.")
        else:
            Submission.objects.create(student=request.user, deliverable=deliverable, **details)
            messages.success(request, f"Your file for {deliverable.title} was uploaded.")
        return redirect("student_home")
    return render(request, "progress/submit.html", {"form": form, "deliverable": deliverable, "existing": existing})


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


@login_required
def student_detail(request, student_id):
    """One student's full picture.

    The student's own supervisor sees it and can leave feedback. The coordinator sees it for any
    student, read only. Students and other supervisors get a 404, so they cannot even tell the page exists.
    """
    if request.user.is_coordinator:
        student = get_object_or_404(User, pk=student_id, role="student")
    elif request.user.is_supervisor:
        student = get_object_or_404(User, pk=student_id, role="student", supervisor=request.user)
    else:
        raise PermissionDenied
    can_write = request.user == student.supervisor
    form = FeedbackForm(request.POST or None) if can_write else None
    if request.method == "POST":
        if not can_write:
            raise PermissionDenied
        if form.is_valid():
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
        "feedback": student.feedback_received.select_related("supervisor"),
        "risk": student.risk_scores.first(),
        "form": form,
        "back": "coordinator_home" if request.user.is_coordinator else "supervisor_home",
        "back_text": "The whole cohort" if request.user.is_coordinator else "My students",
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
