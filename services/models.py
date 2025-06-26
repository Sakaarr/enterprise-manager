from django.db import models
from vehicles.models import Vehicle
from users.models import User

class ServiceRecord(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    service_date = models.DateField()
    description = models.TextField()
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)

class Report(models.Model):
    type = models.CharField(max_length=100)
    generated_on = models.DateField()
    data = models.JSONField()
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)