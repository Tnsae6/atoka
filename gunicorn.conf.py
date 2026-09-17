import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atoka_project.settings')

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 2


def on_starting(server):
    import django
    django.setup()

    from django.core.management import call_command
    call_command('migrate', '--run-syncdb', verbosity=0)
    call_command('collectstatic', '--noinput', verbosity=0)

    from django.contrib.auth.models import User
    from core.models import UserProfile

    from django.db import connections

    user = User.objects.filter(username='admin').first()
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
    if user is None and password:
        user = User.objects.create_superuser('admin', password=password)
    if user is not None:
        UserProfile.objects.get_or_create(user=user, defaults={'role': 'manager'})

    connections.close_all()
    server.log.info('Initialization complete: migrations and static collection')
