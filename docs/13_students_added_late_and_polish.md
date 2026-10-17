# Students added during the semester, and small fixes found by using the site

## Students added during the semester

Files: `accounts/models.py` (field `tracked_from` and the method `counts`), migration 0004,
`accounts/importer.py`, `risk/scoring.py`, `dashboard/views.py`, `templates/dashboard/_progress.html`.

Problem found on 17 October: two students imported from a csv file were red with 70 on their first day,
because every deadline that had already passed counted as missing, and their earlier work was on Moodle.

Fix: a student has a date, `tracked_from`. The import fills it with today for students, the coordinator
can change it in Admin, and empty means every deadline counts, which is how the first accounts work.
`counts(deliverable)` says whether a deadline is on or after that date. The overdue indicator, the
timeline, the milestone bar, the per student numbers and the cohort counts only use deadlines that count.
Older ones show as "Before your account" in a striped grey block. With no meeting yet, the meeting gap is
counted from that date instead of the semester start.

Result: the same two students are green on their first day and still get the reminder for the next deadline.

Question it answers: what happens to a student who joins late, or a tester added in November?

## Small fixes

- 403, 404 and 500 pages in the site's own style, saying what happened and linking back.
- The feedback box has a label for screen readers.
- On a phone the coordinator's links move to their own row, so the page is never wider than the screen.
- The "replace" link next to a file name no longer breaks in the middle of the word.
- The Admin link only shows to accounts that can open the admin.

Tests: `LateAddedStudentTests` in risk/tests.py, `ImportStartDateTests` in accounts/tests.py,
`ErrorPageTests` in dashboard/tests.py. 100 tests.
