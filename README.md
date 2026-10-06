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
