from django import forms
from .models import Student

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['full_name', 'code', 'date_of_birth', 'class_assigned', 'address', 'parent_name', 'parent_phone', 'profile_image']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        if 'class_assigned' in self.fields:
            self.fields['class_assigned'].widget.attrs['class'] = 'form-select'

from .models import Report
from classes.models import Group

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['group', 'student', 'report_type', 'priority', 'title', 'description', 'is_flagged']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'is_flagged': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, teacher, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter groups assigned to the specific teacher
        self.fields['group'].queryset = Group.objects.filter(teachers=teacher)
        
        # Disable student field until a group is selected (will be handled by AJAX/JS)
        self.fields['student'].queryset = Student.objects.none()
        
        for field_name, field in self.fields.items():
            if field_name != 'is_flagged':
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'
                    
        if 'group' in self.data:
            try:
                group_id = int(self.data.get('group'))
                self.fields['student'].queryset = Student.objects.filter(groups__id=group_id).order_by('full_name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['student'].queryset = Student.objects.filter(groups=self.instance.group).order_by('full_name')
