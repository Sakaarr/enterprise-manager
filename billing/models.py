from django.db import models
from cars.models import Car
from users.models import User
class Bill(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='bills',default=None)
    total_service_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_inventory_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_remaining = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Bill'
        verbose_name_plural = 'Bills'

    def __str__(self):
        return f"Bill for Car {self.car.plate_number} (ID: {self.id})"

    @property
    def is_fully_paid(self):
        return self.amount_remaining <= 0


class PaidBill(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_service_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_inventory_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    entered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
