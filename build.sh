#!/usr/bin/env bash
# what the host runs on every deploy
set -e
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_deliverables
python manage.py ensure_admin
# optional: load the development cohort when the host sets SEED_COHORT=1 and SEED_PASSWORD
if [ "${SEED_COHORT:-0}" = "1" ]; then python manage.py seed_cohort; fi
