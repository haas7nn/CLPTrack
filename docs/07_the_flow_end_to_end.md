# Walkthrough 7: the whole flow, end to end

Written 10 October 2026, after walking every page as each role and fixing what did not join up.

## What was missing

Four things looked finished on their own but did not connect.

1. A supervisor could write feedback, and nobody ever saw it. The student timeline now has a
   "Feedback from your supervisor" card, newest first.
2. A student could attach a note to an upload, and the supervisor never saw it. The student page now
   shows the note under that deliverable, with the file name and the upload date.
3. The coordinator could see names on the cohort page but could not open anyone. The names are links
   now. The coordinator gets the same page the supervisor gets, read only, no feedback box. A student
   with no supervisor used to be invisible on that page, they now appear in a group called
   "No supervisor yet".
4. A student could upload once and never correct it, although feedback invites exactly that. There is a
   "replace" link beside the file name. The new file takes the place of the old one and the first upload
   time is kept, because lateness is about when the work first arrived.

The back office also says "CLPTrack admin" now and stays light like the rest of the site.

## The flow, role by role

Coordinator: sign in, Admin, add a supervisor, add a student with their ID, section, email and
supervisor, back to Cohort to see them appear under that supervisor. Download as spreadsheet for everyone.
Click any name to read their page.

Student: sign in, see ten deadlines, upload for the next one with a note, record the weekly meeting with
agreed actions, tick an action off, read the supervisor's feedback, replace a file after feedback.

Supervisor: sign in, see the table with colours and the seven day arrows, the week's activity and the
alerts received, open a student, read the notes, the breakdown and the chart, leave feedback, export.

Every morning: the daily job scores everyone, emails the student about deadlines three days and one
day away with nothing uploaded, and emails the supervisor when a student changes colour.

## Examiner questions

Why does a replaced file keep the first time? Because the score punishes late arrival, not revision.
If a second upload reset the time, a student who improved their work after feedback would be marked
late for doing the right thing.

Why can the coordinator read but not write feedback? Feedback is part of the supervision relationship.
The coordinator oversees the cohort, they do not supervise the student.

Why 404 and not 403 for another supervisor's student? A 403 would confirm that the student exists.

## Tests

42 tests. The new ones: the student sees the feedback, the supervisor sees the note, the coordinator
can read but a POST is refused, a student cannot open the detail page, a student without a supervisor
is still listed, and a second upload replaces the first and keeps its time.
