from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import InventoryItem, Supplier, ProductCategory
from django.core.mail import send_mail
from django.conf import settings

@receiver(post_save, sender=InventoryItem)
def inventory_saved(sender, instance, created, **kwargs):
    action = "created" if created else "updated"
    print(f"Inventory item {action}: {instance.name}")

    if instance.is_low_stock():
        print(f"⚠ LOW STOCK ALERT for {instance.name} (Stock: {instance.quantity_in_stock})")
        # Future: Send email / dashboard notification

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
    

@receiver(post_save, sender=InventoryItem)
def check_low_stock(sender, instance, **kwargs):
    if instance.quantity_in_stock <= instance.low_stock_threshold:  # assuming you add this field
        # Log or send alert
        send_mail(
            subject="Low Stock Alert",
            message=f"Product '{instance.name}' has low stock: {instance.quantity_in_stock}",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=["axortechnp@gmail.com"]
        )