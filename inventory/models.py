from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=255, unique=True)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ProductCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    
class InventoryItem(models.Model):
    UNIT_CHOICES = [
        ('pcs', 'Pieces'),
        ('ltr', 'Litre'),
        ('kg', 'Kilogram'),
        ('mtr', 'Meter'),
        ('box', 'Box'),
        ('set', 'Set'),
        # Add more units as needed
    ]

    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, related_name="items")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name="items")

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    quantity_in_stock = models.PositiveIntegerField(default=0)
    standard_rate = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='pcs')

    low_stock_threshold = models.PositiveIntegerField(default=5)

    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_low_stock(self):
        return self.quantity_in_stock <= self.low_stock_threshold

    def __str__(self):
        return f"{self.name} (Stock: {self.quantity_in_stock} {self.unit})"