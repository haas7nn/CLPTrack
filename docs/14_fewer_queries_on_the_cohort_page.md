# Fewer database queries on the cohort page

Files: `dashboard/views.py` (class `CohortRecords`, and `timeline_for`, `summary_for`, `red_days`,
`deliverable_stats`, `coordinator_home`, `supervisor_home`, `export_csv`), `dashboard/tests.py`.

Problem: the coordinator page asked the database about seven questions for every student. Each summary
looked up the student's submissions, the deliverables, the latest score, the score a week ago and the last
meeting, and every submission then looked up its deliverable again to work out how late it was. Each
supervisor group and each deliverable added more. Measured with ten students the page needed 91 queries,
with twenty it needed 164, so a class of forty would need about 310 for one page.

Fix: `CohortRecords` loads each kind of record once for the whole group: the deliverables, all
submissions (without the file contents), the score history as dates and colours only, the full latest
score row for each student, the last meeting that counts and the meetings waiting for confirmation. The
summaries, the red streak, the deliverable table and the waiting counts are then worked out in memory.
Students are fetched once and shared out to their supervisor's group. The supervisor page and the
spreadsheet export use the same records. Called without records, the functions still work on their own,
so the student page and the student detail page are unchanged.

Result: 12 queries with ten students and still 12 with twenty, on the cohort page. The numbers on every
page are the same as before, all earlier tests pass unchanged.

Question it answers: will the site stay fast with a whole cohort, and how do you know?

Tests: `CohortPageQueryTests` in dashboard/tests.py counts the queries on the cohort page, the export and
a supervisor page, adds ten more students, and checks the counts stay the same.
