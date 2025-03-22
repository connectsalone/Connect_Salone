web: waitress-serve --listen=0.0.0.0:8000 connect_salone.wsgi:application
#or works good with external database
web: python manage.py migrate && gunicorn connect_salone.wsgi


