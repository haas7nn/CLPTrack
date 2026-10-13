# Walkthrough 8: the cohort dashboard for the coordinator

Written 13 October 2026. This is the feature to lead with when someone asks what the system gives the
course, beyond one supervisor's list.

## What the page shows

Top to bottom on `/coordinator/`:

1. The strip: students, supervisors, how many are green, amber and red, deliverables missing in total.
2. Students who need attention: every amber and red student, worst first, with their supervisor, the
   seven day arrow, and the main reason in plain words.
3. Colours over the semester: one stacked bar per day, green, amber and red.
4. Deliverables across the cohort: for each of the ten, how many handed in, how many late, how many
   missing, and a bar for the share handed in. A deliverable that is not due yet shows the days left.
5. Last supervision meeting: students counted into four groups, this week, one to two weeks, more than
   two weeks, never.
6. By supervisor: one line each with students, colours, average score, missing work, and how many have
   had no meeting in two weeks.
7. Everyone, by supervisor: the name chips, each a link to that student's page.

## Where the numbers come from

All of it is counting, done in `dashboard/views.py`, from records that already exist.

`main_reason(risk)` looks at the saved breakdown of a score and returns the indicator with the most
points, in plain words from `INDICATOR_WORDS`.

`deliverable_stats(students, now)` walks the ten deliverables. A student counts once per deliverable.
Missing is only counted after the due date.

`meeting_stats(summaries, today)` puts each student in one of four groups by the date of their last
meeting.

`colour_history()` asks the database for the number of scores per day and colour, one query.

`coordinator_home` calls `summary_for` for every student, the same function the supervisor page and the
spreadsheet use, so the three can never disagree.

## Examiner questions

Why no machine learning? Three reasons. There is no past data to train on, this is the first semester the
records exist. Student records are private, so they could not be shared or pooled to build a model. And
a decision about a person needs a reason the supervisor can read, which a weighted score gives and most
models do not.

Does the "main reason" add a new rule? No. It only reads the breakdown that the score already saved and
names the largest part.

Is the average score per supervisor fair to a supervisor? It is a description, not a judgement. It is on
the coordinator's page only, beside the count of students with no recent meeting, which is the thing a
coordinator can act on.

## Tests

Five tests cover this page. They build two students with known records and check the deliverable counts, the
attention list and its reason, the meeting groups and the supervisor line, and the colour history.
