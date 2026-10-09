# Walkthrough 6: files in the database, the development cohort, email and the new look

Written 9 October 2026. Read this before the weekly explain back session.

## Files live in the database now

The free host wipes its disk on every deploy, so a file saved on disk would vanish with the next fix.
`Submission` now holds the file's bytes in a `data` column with `filename`, `content_type` and `size`.
The upload view reads the file into the row; a `download` view sends the bytes back with the original
name, after checking that the person asking is the student, their supervisor or the coordinator.

Examiner question: is a database the right place for files? For a few hundred documents under 20 MB,
yes, it is simpler and it is backed up with everything else. At a larger scale you would use object
storage, and the thesis says so.

## The development cohort

`seed_cohort` builds six students under `supervisor1`, each with a different story, by walking day by day
from three weeks ago to today, creating that day's submissions, meetings and feedback, then computing and
storing that day's score. So the history chart is consistent with the records. It runs on the host when
`SEED_COHORT=1` and `SEED_PASSWORD` are set, and it does nothing if the cohort already has history.

## Email through Brevo

The host blocks outgoing mail ports. `notifications/brevo.py` is a small Django email backend that posts
each message to Brevo's HTTPS API instead. It is switched on by `BREVO_API_KEY`; without it the settings
fall back to a plain mail server with a ten second timeout. The sender must be an address Brevo has
verified. `/tasks/test-email/`, token protected like the daily job, sends one test message, and the
GitHub workflow "test email" calls it.

## The new look

One stylesheet, `dashboard/static/dashboard/app.css`, and the templates. Colours come from the
Polytechnic Moodle theme: navy header, orange for the active page, light page, Inter. Each role's home
page opens with a stat strip. The supervisor dashboard shows a trend arrow beside each score (change over
seven days), the week's uploads and meetings, and the emails the system sent. The student timeline has a
"What to do next" card built from the five indicators, overdue uploads first.

Examiner question: where do the next steps come from? From `next_steps()` in `dashboard/views.py`. It
reads the same records the score reads, so the advice and the score can never disagree.

## Deploys

Render did not deliver push events, so `.github/workflows/deploy.yml` calls the service's deploy hook on
every push to main. `daily.yml` runs the daily job at 06:00 Bahrain time. `test-email.yml` is run by hand.

## Tests

36 tests. New ones cover the download permissions, the bytes being stored, the cohort command, early
uploads being counted separately, the next steps text, the test email address and the Brevo backend.
