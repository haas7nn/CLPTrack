# Walkthrough 4: the coordinator page, the student score table, and going online

Written 6 October 2026. Read this before the weekly explain back session.

## What was added

1. **Students see their own score.** The "Why this score" table that the supervisor sees on the student
   detail page is now one shared template, `templates/risk/_breakdown.html`, and the student timeline
   includes it too. One file, used in two places, so the two pages can never drift apart.
2. **The coordinator page** (`dashboard/views.py`, `coordinator_home`). The coordinator signs in and sees
   every supervisor with their students, each student as a coloured badge with their score, and a count of
   green, amber and red per supervisor. The coordinator also gets a link to the admin site.
3. **Ready for hosting.** The settings now read from the environment instead of being written in the code.

## How the settings work now

`clptrack/settings.py` reads these environment variables. On the laptop none of them are set, so the
defaults apply and nothing changes for development.

| Variable | On the laptop (default) | On the host |
|---|---|---|
| `SECRET_KEY` | a fixed dev key | a long random string |
| `DEBUG` | 1 (on) | 0 (off) |
| `ALLOWED_HOSTS` | 127.0.0.1, localhost | the site's domain |
| `CSRF_TRUSTED_ORIGINS` | empty | https:// plus the domain |
| `DATABASE_URL` | SQLite file | the PostgreSQL address |
| `EMAIL_HOST` and friends | unset, emails print to the console | the SMTP server |

`.env.example` lists them all with placeholder values. The real `.env` is never committed.

Three more files make the host work:

* `requirements.txt` adds gunicorn (the production web server), whitenoise (serves the css and js files),
  dj-database-url (turns `DATABASE_URL` into Django settings) and psycopg (talks to PostgreSQL).
* `Procfile` tells the host how to start the site: `gunicorn clptrack.wsgi`.
* `build.sh` is what the host runs on every deploy: install, collect static files, migrate.

When `DEBUG` is off, the settings also switch on HTTPS only cookies and a redirect from http to https.

## Questions an examiner might ask

* **Why environment variables?** So the same code runs everywhere, and no secret or password is ever in the
  repository. This is the standard approach, called the twelve factor config rule.
* **What is whitenoise for?** Django does not serve static files itself when DEBUG is off. Whitenoise lets
  the app serve them with compression and cache headers, without needing a separate web server.
* **Why gunicorn?** The `runserver` command is for development only. Gunicorn is a proper server that can
  handle several requests at once.
* **Why SQLite on the laptop and PostgreSQL on the host?** SQLite needs no setup, which keeps development
  simple. PostgreSQL is what hosts provide and handles several users at the same time safely. Django hides
  the difference, the models and queries are identical.
* **How do the daily emails run on the host?** The host's scheduler runs `python manage.py run_daily` once a
  day, which scores every student and then sends reminders and alerts.

## Commands you should be able to run

    .venv/bin/python manage.py check --deploy     # Django's own production checklist
    .venv/bin/python manage.py collectstatic      # gathers css and js into staticfiles/
    DEBUG=0 ALLOWED_HOSTS=example.com .venv/bin/python manage.py check
