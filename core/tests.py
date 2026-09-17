import importlib.util
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase, TransactionTestCase

from core.models import UserProfile


class DashboardLayoutTests(TestCase):
    def test_dashboards_render_mobile_navigation_and_scrollable_tables(self):
        for role, url in (
            ('manager', '/manager/'),
            ('waiter', '/waiter/'),
            ('stock_manager', '/stock/'),
        ):
            with self.subTest(role=role):
                user = User.objects.create_user(username=role)
                UserProfile.objects.create(user=user, role=role)
                self.client.force_login(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'aria-controls="navLinks"')
                self.assertContains(response, 'aria-expanded="false"')
                self.assertContains(response, 'id="navOverlay"')
                if role != 'waiter':
                    self.assertContains(response, 'class="table-responsive"')


class SuperuserRegistrationTests(TestCase):
    def setUp(self):
        self.token = secrets.token_urlsafe(32)
        override = self.settings(ADMIN_SETUP_TOKEN=self.token)
        override.enable()
        self.addCleanup(override.disable)
        self.password = secrets.token_urlsafe(32)
        self.data = {
            'username': 'owner', 'password1': self.password,
            'password2': self.password, 'setup_token': self.token,
        }
        self.url = '/eyob26neba/'

    def test_bootstrap_creates_superuser_and_manager_profile(self):
        self.assertContains(self.client.get(self.url), 'Setup token')
        self.assertRedirects(self.client.post(self.url, self.data), '/login/')
        user = User.objects.get(username='owner')
        self.assertTrue(user.is_staff and user.is_superuser)
        self.assertTrue(user.check_password(self.password))
        self.assertEqual(user.profile.role, 'manager')
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
        self.assertTrue(self.client.login(username='owner', password=self.password))

    def test_denies_missing_configuration_and_invalid_token(self):
        with self.settings(ADMIN_SETUP_TOKEN=''):
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
        for token in ('', 'incorrect'):
            self.assertEqual(self.client.post(self.url, {**self.data, 'setup_token': token}).status_code, 403)
        self.assertFalse(User.objects.exists())

    def test_existing_superuser_can_register_without_token(self):
        owner = User.objects.create_superuser('existing', password=self.password)
        self.client.force_login(owner)
        self.assertNotContains(self.client.get(self.url), 'name="setup_token"')
        self.assertRedirects(self.client.post(self.url, {**self.data, 'setup_token': ''}), '/login/', fetch_redirect_response=False)
        self.assertTrue(User.objects.get(username='owner').is_superuser)

    def test_regular_manager_cannot_register_superusers(self):
        User.objects.create_superuser('existing', password=self.password)
        manager = User.objects.create_user('manager', password=self.password, is_staff=True)
        UserProfile.objects.create(user=manager, role='manager')
        self.client.force_login(manager)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
        self.assertFalse(User.objects.filter(username='owner').exists())

    def test_validation_does_not_create_accounts_or_echo_secrets(self):
        for changes in (
            {'password2': 'mismatch'},
            {'password1': '123', 'password2': '123'},
            {'username': 'invalid name!'},
        ):
            response = self.client.post(self.url, {**self.data, **changes})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
            self.assertNotContains(response, self.token)
            self.assertNotContains(response, self.password)
        self.assertFalse(User.objects.exists())
        User.objects.create_user('owner')
        response = self.client.post(self.url, self.data)
        self.assertIn('username', response.context['form'].errors)
        self.assertFalse(User.objects.filter(is_superuser=True).exists())

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(self.url, self.data).status_code, 403)
        self.assertFalse(User.objects.exists())

    def test_profile_failure_rolls_back_account(self):
        from django.db import IntegrityError
        with mock.patch('core.views.UserProfile.objects.create', side_effect=IntegrityError):
            self.assertEqual(self.client.post(self.url, self.data).status_code, 200)
        self.assertFalse(User.objects.exists())


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
        self.assertTrue(self.client.login(username='admin', password='admin123'))
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
