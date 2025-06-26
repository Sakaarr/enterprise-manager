from django.db import models

class PartCategory(models.Model):
    name = models.CharField(max_length=100)

class Part(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(PartCategory, on_delete=models.CASCADE)
    brand = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity_in_stock = models.IntegerField()
    reorder_level = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


