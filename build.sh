#!/usr/bin/env bash
#Exit on error

set -o errexit

# Modify this line as needed for your package manager (pip, poetry, etc)
pip install -r requirements.txt

# Convert static assest files 
python manage.py collectstatic --no-input

# Apply any ouststanding dtatbase migrations
python manage.py migrate