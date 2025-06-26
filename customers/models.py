from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Invoice(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    invoice_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid = models.BooleanField(default=False)
    due_date = models.DateField()
    payment_status = models.CharField(max_length=50)

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    part = models.ForeignKey('inventory.Part', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_service = models.BooleanField(default=False)

class Reminder(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    reminder_date = models.DateField()
    status = models.CharField(max_length=50)
