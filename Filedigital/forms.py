from django import forms
from .models import File, Category

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['file', 'name', 'category', 'file_type']

    category = forms.ModelChoiceField(queryset=Category.objects.all())
