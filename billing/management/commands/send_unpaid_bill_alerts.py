from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from billing.models import Bill

class Command(BaseCommand):
    help = 'Send fortnightly alert for unpaid bills'

    def handle(self, *args, **kwargs):
        unpaid_bills = Bill.objects.filter(is_fully_paid=False)
        if unpaid_bills.exists():
            message_lines = [
                f"Unpaid Bill Alert (Fortnightly Summary)",
                f"Total unpaid bills: {unpaid_bills.count()}",
                ""
            ]
            for bill in unpaid_bills:
                outstanding = bill.total_amount - bill.amount_paid
                message_lines.append(
                    f"Bill #{bill.id} | Car: {bill.service_record.car.plate_number} | "
                    f"Outstanding: {outstanding}"
                )
            
            send_mail(
                subject="Fortnightly Unpaid Bill Summary",
                message="\n".join(message_lines),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ACCOUNTS_TEAM_EMAIL],
                fail_silently=False
            )
            self.stdout.write(self.style.SUCCESS("Fortnightly unpaid bill alert sent."))
        else:
            self.stdout.write(self.style.WARNING("No unpaid bills found."))
