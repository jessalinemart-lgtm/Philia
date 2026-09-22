#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Both are safe to run on every deploy: createsuperuser --noinput no-ops if the user
# already exists, and seed_demo skips itself if the demo project is already there.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput || true
fi
python manage.py seed_demo
