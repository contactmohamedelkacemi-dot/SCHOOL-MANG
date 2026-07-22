from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        return super().create_superuser(username, email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('formateur', 'Formateur'),
        ('stagiaire', 'Stagiaire'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_profile_complete = models.BooleanField(default=True) # Defaults to True for existing users, False for new onboarding
    must_change_password = models.BooleanField(default=False)

    objects = CustomUserManager()

    def __str__(self):
        return self.username

