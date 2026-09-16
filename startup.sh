#!/bin/bash
python manage.py migrate --run-syncdb
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser admin created')
else:
    u = User.objects.get(username='admin')
    if not u.is_superuser:
        u.is_superuser = True
        u.is_staff = True
        u.save()
        print('Admin promoted to superuser')
"
exec gunicorn atoka_project.wsgi:application --bind 0.0.0.0:$PORT --workers 3
