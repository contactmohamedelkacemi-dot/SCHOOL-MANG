from django.db import models
from accounts.models import User

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    date_of_birth = models.DateField()
    class_assigned = models.ForeignKey('classes.Class', on_delete=models.SET_NULL, null=True)
    profile_image = models.ImageField(upload_to='students/')
    address = models.TextField()
    parent_name = models.CharField(max_length=100)
    parent_phone = models.CharField(max_length=20)

    def __str__(self):
        return self.full_name

class Report(models.Model):
    REPORT_TYPES = (
        ('Academic', 'Academic'),
        ('Behavior', 'Behavior'),
        ('Attendance', 'Attendance'),
        ('Other', 'Other')
    )
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Reviewed', 'Reviewed')
    )
    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High')
    )
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.CASCADE, related_name='reports_submitted')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='reports')
    group = models.ForeignKey('classes.Group', on_delete=models.SET_NULL, null=True, blank=True)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    is_flagged = models.BooleanField(default=False, help_text="Flag for immediate admin attention")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report: {self.title} ({self.student.full_name})"
