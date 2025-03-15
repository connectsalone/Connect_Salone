web: gunicorn connect_salone.wsgi:application --log-file -
#or works good with external database
web: python manage.py migrate && gunicorn connect_salone.wsgi


