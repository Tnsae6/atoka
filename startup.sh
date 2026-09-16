#!/bin/sh
python manage.py migrate --run-syncdb
python manage.py collectstatic --noinput
python manage.py shell -c "from django.contrib.auth.models import User; u=User.objects.filter(username='admin').first(); (u or User.objects.create_user('admin','admin@example.com','admin123')).is_superuser=True; (u or User.objects.create_user('admin','admin@example.com','admin123')).is_staff=True; (u or User.objects.create_user('admin','admin@example.com','admin123')).save()"
exec gunicorn atoka_project.wsgi:application --bind 0.0.0.0:$PORT --workers 3