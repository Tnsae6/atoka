import os
import sys


if __name__ == '__main__':
    port = os.environ.get('PORT', '8000')
    os.execv(sys.executable, [
        sys.executable, '-m', 'gunicorn', '--bind', f'0.0.0.0:{port}',
        'atoka_project.wsgi:application',
    ])
