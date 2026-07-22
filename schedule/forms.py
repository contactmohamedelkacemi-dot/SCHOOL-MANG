from django import forms
from .models import GroupSchedule

class GroupScheduleForm(forms.ModelForm):
    day = forms.ChoiceField(
        choices=[
            ('Monday', 'Monday'),
            ('Tuesday', 'Tuesday'),
            ('Wednesday', 'Wednesday'),
            ('Thursday', 'Thursday'),
            ('Friday', 'Friday'),
            ('Saturday', 'Saturday'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = GroupSchedule
        fields = ['group', 'teacher', 'module', 'day', 'session_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
        self.fields['session_number'].required = True

    def clean(self):
        cleaned_data = super().clean()
        group = cleaned_data.get('group')
        teacher = cleaned_data.get('teacher')
        day = cleaned_data.get('day')
        session_number = cleaned_data.get('session_number')
        
        if group and day and session_number:
            # Check if this exact slot for this group is already taken
            group_conflict = GroupSchedule.objects.filter(group=group, day=day, session_number=session_number)
            if self.instance and self.instance.pk:
                group_conflict = group_conflict.exclude(pk=self.instance.pk)
            if group_conflict.exists():
                raise forms.ValidationError("This group already has a class at this session.")
                
        if teacher and day and session_number:
            # Check if teacher is assigned to ANY group at this time
            teacher_conflict = GroupSchedule.objects.filter(teacher=teacher, day=day, session_number=session_number)
            if self.instance and self.instance.pk:
                teacher_conflict = teacher_conflict.exclude(pk=self.instance.pk)
            if teacher_conflict.exists():
                raise forms.ValidationError("This teacher is already assigned to another group at this time.")
        
        return cleaned_data
