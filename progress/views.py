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


def student_for(viewer, student_id, allow_self=False):
    """Finds a student the viewer is allowed to see, or stops with 403 or 404.

    The coordinator may see anyone, a supervisor only their own students. With allow_self a student
    may see themselves, which the printable report uses.
    """
    if viewer.is_coordinator:
        return get_object_or_404(User, pk=student_id, role="student")
    if viewer.is_supervisor:
        return get_object_or_404(User, pk=student_id, role="student", supervisor=viewer)
    if allow_self and viewer.is_student and viewer.pk == student_id:
        return viewer
    raise PermissionDenied


@login_required
def student_report(request, student_id):
    """One page about one student, laid out to print or save as PDF and take to a meeting."""
    student = student_for(request.user, student_id, allow_self=True)
    history = list(student.risk_scores.order_by("scored_on").values_list("scored_on", "score"))
    # the chart is drawn as a plain line, so it prints the same on every printer
    width, height = 640, 120
    step = width / (len(history) - 1) if len(history) > 1 else 0
    points = " ".join(f"{round(i * step, 1)},{round(height - score * height / 100, 1)}" for i, (_, score) in enumerate(history))
    return render(request, "progress/report.html", {
        "student": student,
        "rows": timeline_for(student),
        "meetings": student.meetings.prefetch_related("actions"),
        "feedback": student.feedback_received.select_related("supervisor"),
        "risk": student.risk_scores.first(),
        "chart": {"points": points, "width": width, "height": height,
                  "first": history[0][0] if history else None, "last": history[-1][0] if history else None},
        "printed_on": timezone.localdate(),
        "back": "student_home" if request.user.is_student else "student_detail",
    })


@login_required
def student_detail(request, student_id):
    """One student's full picture.

    The student's own supervisor sees it and can leave feedback. The coordinator sees it for any
    student, read only. Students and other supervisors get a 404, so they cannot even tell the page exists.
    """
    student = student_for(request.user, student_id)
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


@role_required("supervisor")
@require_POST
def meeting_review(request, meeting_id):
    """A supervisor says whether a meeting their student recorded really happened.

    Only the student's own supervisor can do it. A meeting marked as not held stops counting
    towards the score from the next daily run.
    """
    meeting = get_object_or_404(Meeting, pk=meeting_id, student__supervisor=request.user)
    decision = request.POST.get("decision")
    if decision not in (Meeting.Status.CONFIRMED, Meeting.Status.REJECTED):
        raise PermissionDenied
    meeting.status = decision
    meeting.reviewed_at = timezone.now()
    meeting.save()
    messages.success(request, "Meeting confirmed." if decision == Meeting.Status.CONFIRMED
                     else "Meeting marked as not held. It no longer counts towards the score.")
    return redirect("student_detail", student_id=meeting.student_id)


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
