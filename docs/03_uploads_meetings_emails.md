# Walkthrough 3: uploads, meetings, feedback, the daily job and the emails

Written 6 October 2026. Read with walkthroughs 1 and 2.

## What was added

| Part | Files | What it does |
|---|---|---|
| Uploads | `progress/forms.py`, `progress/views.py` (`submit`), `progress/templates/progress/submit.html` | A student uploads one file for one deliverable. The form refuses files that are not documents or images, and anything over 20 MB. |
| Meetings | `progress/views.py` (`meetings`, `action_done`), `meetings.html` | A student records a meeting and types the agreed actions one per line. Each line becomes an Action row with a "done" button. |
| Feedback | `progress/views.py` (`student_detail`), `student_detail.html` | A supervisor opens one of their students, sees everything, and leaves a comment. |
| Daily scoring | `risk/management/commands/score_students.py` | Works out today's score for every student and saves one row per student per day. |
| Emails | `notifications/emails.py`, `send_notifications.py`, `NotificationLog` | Reminders to students 3 days and 1 day before a deadline they have not uploaded for, and an alert to the supervisor when a student changes colour. |
| One daily command | `risk/management/commands/run_daily.py` | Runs the scoring and then the emails. This is the one thing the host runs each day. |
| Why this score | `student_detail.html` | A table of the five indicators with value, weight and points, and a chart of the score over time. |
| Charts | `supervisor_home.html` | Green, amber and red counts, and a bar per student of how much they have submitted. |

## Three design decisions, and why

1. **Agreed actions are typed one per line.** The simplest possible way to enter a list. Each line becomes
   its own row so it can be ticked off separately, and the risk score counts the open ones.
2. **Every email is logged with a reference.** The reference is a short text like `reminder:3:1`, meaning
   deliverable 3, one day before. Before sending, the code checks the log for that reference, so the same
   email can never go out twice, even if the daily job runs twice.
3. **One daily command, not several.** `run_daily` calls the scoring and then the emails, in that order,
   because the alerts need today's scores to exist first. The host only has to schedule one thing.

## How safety is checked

* A student can only tick their own actions. `action_done` looks the action up with
  `meeting__student=request.user`, so another student's action simply does not exist for them (404).
* A supervisor can only open their own students. `student_detail` looks the student up with
  `supervisor=request.user`, again a 404 otherwise.
* The upload form checks the file name ending and the size before saving anything.
* All of these have tests in `progress/tests.py` and `notifications/tests.py`. There are 19 tests now.

## What the emails look like

While developing, emails are not really sent. Django prints them to the terminal where the server is
running, which is enough to check the wording. On the real host, the MAILERS setting in `settings.py`
will point at an SMTP service instead, with no code changes.

## Questions an examiner might ask

* **What stops the system emailing a student every day about the same deadline?** The notification log
  and the reference text. One reminder at 3 days, one at 1 day, never more.
* **What if the daily job does not run one day?** Nothing breaks. The next run scores that day. The
  missing day simply has no row in the history, which the chart shows as a gap.
* **Why does the supervisor only get an email when the colour changes?** A daily email for every student
  would be ignored. A change of colour is the moment that needs attention.
* **How do you know the formula is right?** The worked example test checks every indicator and the total,
  and the "Why this score" table on the student page shows the same numbers, so anyone can check by hand.
