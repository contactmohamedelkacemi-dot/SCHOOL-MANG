from django.db import models
from students.models import Student
from classes.models import Module

class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    score = models.FloatField()

    def __str__(self):
        return f"{self.student} - {self.module} - {self.score}"
