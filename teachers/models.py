from django.db import models
from accounts.models import User

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, null=True, blank=True)
    cin = models.CharField(max_length=20, unique=True)
    profile_image = models.ImageField(upload_to='teachers/', null=True, blank=True)
    cv = models.FileField(upload_to='teachers/cv/', null=True, blank=True)
    address = models.TextField()
    date_of_birth = models.DateField()
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    specialty = models.CharField(max_length=100)

    def __str__(self):
        return self.full_name
