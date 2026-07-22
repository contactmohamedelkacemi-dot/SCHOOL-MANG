from django.db import models
from classes.models import Class, Module, Group
from teachers.models import Teacher

class Schedule(models.Model):
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    time = models.TimeField()

    def __str__(self):
        return f"{self.class_assigned} - {self.module} ({self.day} {self.time})"

class GroupSchedule(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    time = models.TimeField(null=True, blank=True)
    
    SESSION_CHOICES = [
        (1, '08:00 - 10:00'),
        (2, '10:00 - 12:00'),
        (3, '14:00 - 16:00'),
        (4, '16:00 - 18:00'),
    ]
    session_number = models.IntegerField(choices=SESSION_CHOICES, null=True, blank=True)
    duration = models.IntegerField(default=120)

    class Meta:
        unique_together = ('group', 'day', 'session_number')

    def __str__(self):
        return f"{self.group} - {self.module} ({self.day} Session {self.session_number})"
