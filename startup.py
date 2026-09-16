import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atoka_project.settings')

import django
django.setup()

from django.core.management import call_command

# Run migrations (creates DB tables if first run)
call_command('migrate', '--run-syncdb', verbosity=0)

# Collect static files for Whitenoise
call_command('collectstatic', '--noinput', verbosity=0)

# Ensure admin user exists with profile
from django.contrib.auth.models import User
from core.models import UserProfile

if not User.objects.filter(username='admin').exists():
    u = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    UserProfile.objects.get_or_create(user=u, role='manager')
    print('Admin user created')
else:
    u = User.objects.get(username='admin')
    UserProfile.objects.get_or_create(user=u, defaults={'role': 'manager'})
    print('Admin profile ensured')

print('Startup complete - starting gunicorn...')

# Start gunicorn
from gunicorn.app.wsgiapp import run
run()