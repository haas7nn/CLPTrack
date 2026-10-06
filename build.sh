#!/usr/bin/env bash
# what the host runs on every deploy
set -e
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_deliverables
python manage.py ensure_admin
