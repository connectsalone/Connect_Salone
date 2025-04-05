web: gunicorn connect_salone.wsgi:application --workers 1
web: python manage.py migrate && gunicorn events.wsgi


