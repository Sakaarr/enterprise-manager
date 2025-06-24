from django.contrib.auth.models import AbstractUser
from django.db import models
from users.managers import UserManager
from typing import ClassVar
from django.core.validators import RegexValidator
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
    
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def __str__(self) -> str:
        return self.email