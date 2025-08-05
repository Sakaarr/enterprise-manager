# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from django.core.mail import send_mail
# from django.conf import settings
# from .models import Payment, Bill

# @receiver(post_save, sender=Payment)
# def check_unpaid_bill_after_payment(sender, instance, created, **kwargs):
#     bill = instance.bill
#     if not bill.is_fully_paid:
#         send_unpaid_bill_alert(bill)

# def send_unpaid_bill_alert(bill):
#     outstanding = bill.total_amount - bill.amount_paid
#     send_mail(
#         subject=f"Unpaid Bill Alert - Bill #{bill.id}",
#         message=(
#             f"Bill #{bill.id} for car {bill.service_record.car.plate_number} "
#             f"still has an outstanding amount of {outstanding}."
#         ),
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         recipient_list=["axortechnp@gmail.com"],  # define in settings.py
#         fail_silently=True
#     )
