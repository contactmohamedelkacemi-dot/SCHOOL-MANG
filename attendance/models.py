from django.db import models
from students.models import Student
from classes.models import Module, Group

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    status = models.CharField(max_length=20)

    justification_file = models.ImageField(upload_to='justifications/', null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.date}"

class AttendanceSession(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='sessions')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='attendance_sessions')
    date = models.DateField()
    session_number = models.IntegerField() # 1, 2, 3, or 4
    status = models.CharField(max_length=20, choices=[('Present', 'Present'), ('Absent', 'Absent'), ('Late', 'Late')])

    class Meta:
        unique_together = ('student', 'date', 'session_number')

    def __str__(self):
        return f"{self.student} - {self.date} (Session {self.session_number}) - {self.status}"

class Justification(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='justifications')
    date = models.DateField()
    reason = models.TextField()
    image = models.ImageField(upload_to='justifications/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        unique_together = ('student', 'date')

    def __str__(self):
        return f"Justification for {self.student} on {self.date} - {self.status}"

class JustificationSession(models.Model):
    justification = models.ForeignKey(Justification, on_delete=models.CASCADE, related_name='session_links')
    session_number = models.IntegerField()

    class Meta:
        unique_together = ('justification', 'session_number')

    def __str__(self):
        return f"Session {self.session_number} for {self.justification}"

class StudentRisk(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='risk_profile')
    risk_score = models.FloatField(default=0.0)
    risk_level = models.CharField(max_length=20, choices=[('Safe', 'Safe'), ('At Risk', 'At Risk'), ('Critical', 'Critical')], default='Safe')
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - {self.risk_level} ({self.risk_score})"

class Notification(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    type = models.CharField(max_length=50) # e.g. 'RISK_LEVEL_UP', 'CONSECUTIVE_ABSENCES'
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.type} - {self.student}"
