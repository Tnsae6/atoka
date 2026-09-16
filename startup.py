import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atoka_project.settings')

import django
django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User

# Run migrations
call_command('migrate', '--run-syncdb', verbosity=0)

# Collect static files
call_command('collectstatic', '--noinput', verbosity=0)

# Create admin user
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Admin created')
else:
    u = User.objects.get(username='admin')
    u.is_superuser = True
    u.is_staff = True
    u.save()
    print('Admin verified')

# Run seed_data if available
try:
    call_command('seed_data', verbosity=0)
    print('Seed data done')
except Exception as e:
    print(f'Seed data skipped: {e}')

# Start gunicorn
from gunicorn.app.wsgiapp import run
run()
