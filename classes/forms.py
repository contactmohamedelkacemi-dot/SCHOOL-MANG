from django import forms
from .models import Class, Group

class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'class_assigned', 'teachers', 'students']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        if 'class_assigned' in self.fields:
            self.fields['class_assigned'].widget.attrs['class'] = 'form-select'
        if 'teachers' in self.fields:
            self.fields['teachers'].widget.attrs['class'] = 'form-select'
        if 'students' in self.fields:
            self.fields['students'].widget.attrs['class'] = 'form-select'
