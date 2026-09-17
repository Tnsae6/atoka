import importlib.util
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TransactionTestCase

from core.models import UserProfile


class GunicornStartupTests(TransactionTestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        override = self.settings(STATIC_ROOT=Path(temporary.name), DEBUG=False)
        override.enable()
        self.addCleanup(override.disable)
        self.environment = mock.patch.dict('os.environ', {'DJANGO_SUPERUSER_PASSWORD': ''})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def load_config(self):
        spec = importlib.util.spec_from_file_location(
            'gunicorn_conf_test', settings.BASE_DIR / 'gunicorn.conf.py',
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_bind_uses_port_env(self):
        with mock.patch.dict('os.environ', {'PORT': '12345'}):
            self.assertEqual(self.load_config().bind, '0.0.0.0:12345')

    def test_startup_serves_login_and_static_files_without_debug(self):
        self.load_config().on_starting(mock.Mock())
        self.assertEqual(self.client.get('/login/').status_code, 200)
        response = self.client.post('/login/', {'username': 'missing', 'password': 'invalid'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='admin').exists())
        for path in ('core/css/style.css', 'core/js/app.js'):
            response = self.client.get('/static/' + path)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(b''.join(response.streaming_content))
            response.close()

    def test_static_files_available_before_collection(self):
        self.assertEqual(list(settings.STATIC_ROOT.iterdir()), [])
        for path, content_type in (
            ('core/css/style.css', 'text/css'),
            ('core/js/app.js', 'text/javascript'),
        ):
            response = self.client.get('/static/' + path)
            self.assertEqual(response.status_code, 200)
            self.assertIn(content_type, response['Content-Type'])
            self.assertTrue(b''.join(response.streaming_content))
            response.close()
        self.assertEqual(self.client.get('/static/nonexistent.css').status_code, 404)

    def test_startup_creates_admin_only_with_configured_password(self):
        password = secrets.token_urlsafe(32)
        config = self.load_config()
        with mock.patch.dict('os.environ', {'DJANGO_SUPERUSER_PASSWORD': password}):
            config.on_starting(mock.Mock())
        user = User.objects.get(username='admin')
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(password))
        self.assertEqual(user.profile.role, 'manager')
        with mock.patch.dict('os.environ', {'DJANGO_SUPERUSER_PASSWORD': secrets.token_urlsafe(32)}):
            config.on_starting(mock.Mock())
        user.refresh_from_db()
        self.assertTrue(user.check_password(password))
        self.assertEqual(UserProfile.objects.filter(user=user).count(), 1)

    def test_migration_failure_stops_startup(self):
        with mock.patch('django.core.management.call_command', side_effect=RuntimeError('migration failed')):
            with self.assertRaisesRegex(RuntimeError, 'migration failed'):
                self.load_config().on_starting(mock.Mock())
