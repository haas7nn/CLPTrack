# Two small additions: red for two weeks, and feedback marked as addressed

## Red for two weeks

File: `dashboard/views.py`, the function `red_days` and the constant `STUCK_DAYS = 14`.

The daily job already stores one RiskScore row per student per day. `red_days` reads those rows newest
first and stops at the first one that is not red, so it counts the unbroken run of red days. If the
latest row is not red the answer is 0.

On the coordinator page every amber or red student gets `red_days`, and `stuck` is true at 14 or more.
The attention list is sorted stuck first, then worst score. The page says "Red for 15 days, follow up
with the supervisor" under the name, and a line above the list counts how many are stuck.

Why 14: two weekly meetings have passed and the colour did not change, so the supervisor alone has
not moved the student. It is a constant, so it is one line to change.

Question it answers: how does the coordinator know a student is getting help?

## Feedback marked as addressed

Files: `progress/models.py` (field `addressed_at` on Feedback, migration 0006), `progress/views.py`
(`feedback_addressed`), `progress/urls.py`, and the two templates that show feedback.

The student sees a "Mark as addressed" button under each comment on their timeline. The view only
accepts POST, and finds the comment with `student=request.user`, so another student gets 404 and a
supervisor gets 403. It saves the time once and never clears it.

The supervisor's student page shows "Pending" in amber or "Addressed" with the date in green beside
each comment.

Question it answers: did the student act on what I said?

Tests: `StuckInRedTests` in dashboard/tests.py, `FeedbackAddressedTests` in progress/tests.py. 93 tests.
