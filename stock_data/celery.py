from __future__ import absolute_import
import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock_data.settings')
app = Celery('stock_data')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')

app.conf.beat_schedule = {
    'task-number-one': {
        'task': 'core.tasks.save_stock_data',
        'schedule': crontab(hour="10,11,12,13,14,15", minute="*/5", day_of_week="2,3,4,5,6"),

    },
}

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
