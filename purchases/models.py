from django.db import models
from suppliers.models import Supplier
from inventory.models import Part

class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    purchase_date = models.DateField()
    status = models.CharField(max_length=50)

class PurchaseItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)