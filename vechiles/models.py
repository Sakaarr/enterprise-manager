from django.db import models
from customers.models import Customer
from users.models import User

class Vehicle(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    plate_number = models.CharField(max_length=20)
    model = models.CharField(max_length=100)
    year = models.IntegerField()

class GatePass(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE)
    issued_date = models.DateTimeField()
    purpose = models.TextField()
    return_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50)
