# Walkthrough 9: the supervisor confirms meetings

Written 13 October 2026. This closes the question "what if a student records a meeting that never
happened".

## The problem

A student records their own meetings, and the score counts the days since the last one. Before this
change nobody had to agree that the meeting took place, so a student could record one to stay green.

## What changed

Every meeting now has a status with three values, kept in `Meeting.status`:

- waiting, the default when a student records it
- confirmed, the supervisor pressed "Confirm it happened"
- rejected, the supervisor pressed "This did not happen"

The buttons are on the supervisor's page for that student, under each meeting. Only the student's own
supervisor can press them, the view is `meeting_review` in `progress/views.py`. Another supervisor gets a
404 and a student gets a 403.

## What it does to the score

One rule: a rejected meeting does not count. `Meeting.counted()` returns every meeting except the
rejected ones, and the scoring, the dashboards and the advice card all read meetings through it. The
actions agreed in a rejected meeting are dropped too.

A waiting meeting still counts. That is deliberate. If only confirmed meetings counted, a supervisor
who is slow to click would turn a good student red, and the score would measure the supervisor.

## What each person sees

Student: a label on every meeting, and if one was rejected a red line saying it does not count, plus a
line at the top of "What to do next".

Supervisor: "Meetings to confirm" in the strip on their home page, and the two buttons per meeting.

Coordinator: "Meetings waiting for confirmation" for the cohort, and a "To confirm" number per supervisor.

## Examiner questions

Can a student still cheat? Only until the supervisor looks. The meeting shows as waiting to everyone,
and the supervisor sees the count on their home page.

Why not block the score until confirmed? Because then a busy supervisor punishes the student.

Can the supervisor change their mind? Yes, the other button stays available, and the time of the last
decision is kept in `reviewed_at`.

## Tests

Seven tests cover this: a new meeting waits, a supervisor confirms, only the student's own supervisor can
review, a rejected meeting and its actions stop counting, the student is told, an unknown decision is
refused, and the coordinator's waiting count.
