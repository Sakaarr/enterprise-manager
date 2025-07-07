from django.contrib.auth.models import AbstractUser
from django.db import models
from users.managers import UserManager
from typing import ClassVar
from django.core.validators import RegexValidator


class Role(models.Model):
    name = models.CharField(max_length=100)
    permissions = models.TextField()
    
class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=100, null=True, blank=True)
    password = models.CharField(max_length=150)
    USERNAME_FIELD = "email"
    avatar = models.ImageField(upload_to='profile_images', null=True, blank=True)
    phone_regex = RegexValidator(
        regex=r'^\d{10}$',
        message="Phone number must be 10 digits."
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, default=None, null=True, blank=True)
    
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def __str__(self) -> str:
        return self.email
    
    
class Article(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    keywords = models.CharField(max_length = 100)  # Stores keywords as a list of strings
    category = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to='aaecphotos', null=True, blank=True)
    featured_image = models.ImageField(upload_to='aaecphotos', null=True, blank=True)
    featured = models.BooleanField(default=False)

    def __str__(self):
        return self.title
    
    
class ContactUs(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"Message from {self.first_name} {self.last_name} - {self.subject}"
    
    
class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    position = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='profile_photos', blank=True, null=True)

    def __str__(self):
        return self.name