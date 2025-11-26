from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import InventoryItem, Supplier, ProductCategory
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=InventoryItem)
def inventory_saved(sender, instance, created, **kwargs):
    action = "created" if created else "updated"
    print(f"Inventory item {action}: {instance.name}")

    if instance.is_low_stock():
        print(f"⚠ LOW STOCK ALERT for {instance.name} (Stock: {instance.quantity_in_stock})")
        # Send email alert with error handling
        try:
            send_mail(
                subject="Low Stock Alert",
                message=f"Product '{instance.name}' has low stock: {instance.quantity_in_stock}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=["axortechnp@gmail.com"],
                fail_silently=False,
            )
        except Exception as e:
            # Log the error but don't break the product creation
            logger.error(f"Failed to send low stock alert email for {instance.name}: {str(e)}")
            print(f"⚠ Failed to send email alert: {str(e)}")

@receiver(post_delete, sender=InventoryItem)
def inventory_deleted(sender, instance, **kwargs):
    print(f"Inventory item deleted: {instance.name}")

@receiver(post_save, sender=Supplier)
def supplier_saved(sender, instance, created, **kwargs):
    action = "created" if created else "updated"
    print(f"Supplier {action}: {instance.name}")

@receiver(post_delete, sender=Supplier)
def supplier_deleted(sender, instance, **kwargs):
    print(f"Supplier deleted: {instance.name}")

@receiver(post_save, sender=ProductCategory)
def category_saved(sender, instance, created, **kwargs):
    action = "created" if created else "updated"
    print(f"Product category {action}: {instance.name}")