# CLPTrack

A progress analytics and early warning system for CLP supervision.
Bahrain Polytechnic, Bachelor of ICT, Programming. Cooperative Learning Project, September to December 2026.
Student: Hasan Fardan, 202301686. Supervisor: Dr Elsayed Elkenawy.

## What it does

Students see their CLP deadlines, upload their work and record their supervision meetings.
Supervisors see all their students on one dashboard with a green, amber or red risk status for each one,
with the reasons behind it, confirm the meetings their students record, and leave feedback.
The coordinator sees the whole cohort with statistics, changes the score weights with a preview of the
effect, and loads accounts from a csv file.

| Who | Pages |
|---|---|
| Student | Timeline, upload and replace a file, meetings and actions, what to do next, feedback, printable report |
| Supervisor | My students, one student in full, confirm meetings, feedback, printable report, spreadsheet |
| Coordinator | Cohort dashboard, any student read only, Add people, Score settings, Admin, spreadsheet |
| Everyone | Change password, reset a forgotten password by email |

Every morning a job scores every student from five indicators, emails students before deadlines and
emails a supervisor when a student changes colour.

## Run it

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python manage.py migrate
    .venv/bin/python manage.py runserver

Then open http://127.0.0.1:8000

## Development accounts

    .venv/bin/python manage.py seed_deliverables   # the CLP deadlines for this semester
    .venv/bin/python manage.py seed_demo           # development accounts
    .venv/bin/python manage.py seed_cohort --password choose-one   # six students with three weeks of history
    .venv/bin/python manage.py shared_password     # asks for one password and sets it on all eight accounts

Development accounts, development only: coordinator (also the admin), supervisor1, student1 to student6.
`seed_demo` gives the first five a starting password written in that command. Run `shared_password` to
replace it with your own. On the host the same command reads `ACCOUNTS_PASSWORD`.
The admin site is at http://127.0.0.1:8000/admin

## Tests

    .venv/bin/python manage.py test

93 tests, about fifty seconds. They cover each indicator and the worked example, the access rule of
every page, uploads, meetings and their confirmation, emails never sent twice, the cohort statistics,
score settings, passwords, loading people from a file and the printable report.

## Putting it online

The code is the same on the laptop and on the host. Only the environment variables differ, see
`.env.example`. `render.yaml` describes the site for Render, which runs `build.sh` on every deploy and
starts the site with gunicorn. The database is a free Neon Postgres, pasted in as `DATABASE_URL`.

The daily job (scores, then emails) is triggered by the GitHub workflow in `.github/workflows/daily.yml`,
which posts to `/tasks/daily/` with the secret token every morning. Two repository secrets are needed:
`SITE_URL` (the site address without a trailing slash) and `DAILY_TASK_TOKEN` (the same value as on Render).

## Walkthroughs

The `docs/` folder has ten plain English notes, one per part of the system, each ending with the
questions an examiner might ask. Read them in order.

## Workflows

- `deploy.yml` tells Render to deploy after every push to main.
- `daily.yml` runs the daily scoring and emails at 06:00 Bahrain time.
- `test-email.yml` sends one test email from the live site, run it by hand with an address.

Email goes through Brevo's API when `BREVO_API_KEY` is set, because the host blocks mail ports.
