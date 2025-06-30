from django.db import models
from cars.models import CarServiceRecord
from inventory.models import InventoryItem

class Bill(models.Model):
    service_record = models.OneToOneField(CarServiceRecord, on_delete=models.CASCADE, related_name="bill")
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def amount_due(self):
        return self.total_amount - self.amount_paid

    @property
    def is_fully_paid(self):
        return self.amount_due <= 0

    def __str__(self):
        return f"Bill for {self.service_record.car} - {self.created_at.date()}"

class BillLineItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.description} - {self.amount}"

class Payment(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="payments")
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_on = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=100, default="cash")  # cash, card, etc.

    def __str__(self):
        return f"{self.paid_amount} on {self.paid_on.date()}"
