web : python manage.py runserver 0.0.0.0:$PORT
worker : celery -A stock_data worker -l info
worker : celery -A stock_data beat -l info