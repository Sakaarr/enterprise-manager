from django.db import models
from users.models import User
from django.utils import timezone

class Car(models.Model):
    SERVICE_CHOICES = [
        ('free',"Free"),
        ('paid', "Paid")
    ]
    plate_number = models.CharField(max_length=20, unique=True)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    color = models.CharField(max_length=50, blank=True, null=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True, default="NA")
    service_type = models.CharField(max_length=10, choices=SERVICE_CHOICES, default='paid')
    kms_reading = models.CharField(max_length=20, blank=True, null=True, default="0")
    car_image = models.ImageField(upload_to='car_images/', blank=True, null=True)
    owner_name = models.CharField(max_length=100)
    owner_contact = models.CharField(max_length=20)
    owner_email = models.EmailField(blank=True, null=True, default="owner@email.com")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cars')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.plate_number} - {self.brand} {self.model}"


class JobEntry(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='job_entries')
    manual_book_number = models.CharField(max_length=50)
    entry_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='job_entries')

    def __str__(self):
        return f"JobEntry {self.manual_book_number} for {self.car.plate_number}"
    
class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    standard_rate = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='services')

    def __str__(self):
        return self.name
    
class CarServiceRecord(models.Model):
    car = models.OneToOneField(Car, on_delete=models.CASCADE, related_name="service_record")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_service_records')

    def __str__(self):
        return f"Service Record for {self.car.plate_number}"

class ServiceEntry(models.Model):
    service_record = models.ForeignKey(CarServiceRecord, on_delete=models.CASCADE, related_name="service_entries")
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    performed_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_entries')

    def __str__(self):
        return f"{self.service_record.car.plate_number} - {self.service.name}"

    class Meta:
        ordering = ['-performed_at']
class InventoryUsage(models.Model):
    service_record = models.ForeignKey(CarServiceRecord, on_delete=models.CASCADE, related_name="inventory_usages")
    product = models.ForeignKey("inventory.InventoryItem", on_delete=models.CASCADE)
    quantity_used = models.PositiveIntegerField()
    used_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='car_inventory_usages')

    def __str__(self):
        return f"{self.product.name} used in {self.service_record}"