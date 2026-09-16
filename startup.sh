#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --run-syncdb

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Setting up admin user..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    u = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created')
else:
    u = User.objects.get(username='admin')
    if not u.is_superuser or not u.is_staff:
        u.is_superuser = True
        u.is_staff = True
        u.save()
        print('Admin promoted')
    else:
        print('Admin already a superuser')
"

echo "Seeding data..."
python manage.py seed_data || true

echo "Starting server..."
exec gunicorn atoka_project.wsgi:application --bind 0.0.0.0:$PORT --workers 3
