from django import forms
from django.conf import settings
from .models import SharedFile, Peer

class FileUploadForm(forms.ModelForm):
    """Form for uploading files to share"""
    
    class Meta:
        model = SharedFile
        fields = ['file_path', 'description']
        widgets = {
            'file_path': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '*/*',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description of your file...',
            }),
        }
        labels = {
            'file_path': 'Choose File',
            'description': 'Description (Optional)',
        }
    
    def clean_file_path(self):
        """Validate file upload"""
        file = self.cleaned_data.get('file_path')
        
        if file:
            # Check file size
            max_size = getattr(settings, 'P2P_MAX_FILE_SIZE', 100 * 1024 * 1024)  # 100MB default
            if file.size > max_size:
                raise forms.ValidationError(
                    f'File too large. Maximum size is {max_size // (1024*1024)}MB.'
                )
            
            # Check if filename is reasonable
            if len(file.name) > 255:
                raise forms.ValidationError('Filename is too long.')
        
        return file

class PeerRegistrationForm(forms.Form):
    """Form for peer registration/login"""
    
    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username',
            'required': True,
        }),
        help_text='Choose a unique username for the P2P network'
    )
    
    def clean_username(self):
        """Validate username"""
        username = self.cleaned_data.get('username')
        
        if username:
            # Check for invalid characters
            if not username.replace('_', '').replace('-', '').isalnum():
                raise forms.ValidationError(
                    'Username can only contain letters, numbers, hyphens, and underscores.'
                )
            
            # Check minimum length
            if len(username) < 3:
                raise forms.ValidationError('Username must be at least 3 characters long.')
        
        return username

class FileSearchForm(forms.Form):
    """Form for searching files"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search files...',
        })
    )
    
    file_type = forms.ChoiceField(
        required=False,
        choices=[],  # Will be set in __init__
        widget=forms.Select(attrs={
            'class': 'form-select',
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically set choices to avoid import errors
        self.fields['file_type'].choices = [('', 'All Types')] + getattr(SharedFile, 'FILE_TYPES', [])
