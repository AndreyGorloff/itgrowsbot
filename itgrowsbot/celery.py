import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings
from django.db import connection

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'itgrowsbot.settings')

app = Celery('itgrowsbot')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'check-scheduler-settings': {
        'task': 'bot.tasks.publish_articles',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes to check scheduler settings
    },
    'generate-articles': {
        'task': 'bot.tasks.generate_scheduled_content',
        'schedule': crontab(minute='*/5'),  # Run every 5 minutes to check if we need to generate content
    },
}

# Ensure database connection is closed after each task
@app.task(bind=True)
def debug_task(self):
    try:
        print(f'Request: {self.request!r}')
    finally:
        connection.close()

# Add task error handler
@app.task(bind=True)
def error_handler(self, exc, task_id, args, kwargs, einfo):
    print(f'Task {task_id} raised exception: {exc}')
    connection.close() 