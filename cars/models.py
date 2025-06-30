# cars/models.py

from django.db import models

class Car(models.Model):
    plate_number = models.CharField(max_length=20, unique=True)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    color = models.CharField(max_length=50, blank=True, null=True)
    year = models.PositiveIntegerField(blank=True, null=True)
    car_image = models.ImageField(upload_to='car_images/', blank=True, null=True)
    owner_name = models.CharField(max_length=100)
    owner_contact = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.plate_number} - {self.brand} {self.model}"


class JobEntry(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='job_entries')
    manual_book_number = models.CharField(max_length=50)
    entry_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"JobEntry {self.manual_book_number} for {self.car.plate_number}"