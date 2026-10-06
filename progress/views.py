"""Pages for handing in work, recording meetings and leaving feedback."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import User
from dashboard.views import role_required, timeline_for
from .forms import FeedbackForm, MeetingForm, SubmissionForm
from .models import Action, Deliverable, Meeting


@role_required("student")
def submit(request, deliverable_id):
    """A student uploads a file for one deliverable."""
    deliverable = get_object_or_404(Deliverable, pk=deliverable_id)
    form = SubmissionForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        submission = form.save(commit=False)
        submission.student = request.user
        submission.deliverable = deliverable
        submission.save()
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
    return render(request, "progress/student_detail.html", {
        "student": student,
        "rows": timeline_for(student),
        "meetings": student.meetings.prefetch_related("actions"),
        "feedback": student.feedback_received.all(),
        "risk": student.risk_scores.first(),
        "form": form,
    })
