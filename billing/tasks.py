# from celery import shared_task
# from django.core.management import call_command

# @shared_task
# def send_fortnightly_unpaid_bill_alerts():
#     call_command('send_unpaid_bill_alerts')
from celery import shared_task

@shared_task
def test_celery_task():
    print("✅ Celery task ran successfully!")
    return "Done"