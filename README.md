# CLPTrack

A progress analytics and early warning system for CLP supervision.
Bahrain Polytechnic, Bachelor of ICT, Programming. Cooperative Learning Project, September to December 2026.
Student: Hasan Fardan, 202301686. Supervisor: Dr Elsayed Elkenawy.

## What it does

Students see their CLP deadlines, upload their work and record their supervision meetings.
Supervisors see all their students on one dashboard with a green, amber or red risk status for each one.

## Run it

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python manage.py migrate
    .venv/bin/python manage.py runserver

Then open http://127.0.0.1:8000

## Sample data for development

    .venv/bin/python manage.py seed_deliverables   # the CLP deadlines for this semester
    .venv/bin/python manage.py seed_demo           # sample accounts

Sample accounts, development only: coordinator (also the admin), supervisor1, student1, student2, student3.
The password for all of them is in accounts/management/commands/seed_demo.py.
The admin site is at http://127.0.0.1:8000/admin

## Tests

    .venv/bin/python manage.py test

## Putting it online

The code is the same on the laptop and on the host. Only the environment variables differ, see
`.env.example`. The host runs `build.sh` on every deploy, starts the site with the command in `Procfile`,
and runs `python manage.py run_daily` once a day.
