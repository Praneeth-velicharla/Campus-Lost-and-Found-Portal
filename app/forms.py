from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import LostItem, FoundItem, UserProfile # Import the new model MatchNotificationStatus here as well

# Assuming you have added the phone_number field to the User model via migration 
# or a related Profile model. For demonstration, we'll save it to the User object.

class CollegeUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="College Email",
        widget=forms.EmailInput(attrs={
            'class': 'w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600',
            'placeholder': 'Enter your college email'
        })
    )
    
    # 👇 NEW FIELD ADDED HERE 👇
    phone_number = forms.CharField(
        required=True,
        label="Phone Number",
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600',
            'placeholder': 'Enter your 10-digit phone number'
        })
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600',
            'placeholder': 'Enter password'
        })
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = User
        # 👇 ADD 'phone_number' to fields 👇
        fields = ("username", "email", "phone_number", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600",
                "placeholder": "Choose a username"
            }),
        }

    # ... clean_email (unchanged) ...
    def clean_email(self):
        email = self.cleaned_data.get("email")
        allowed_domains = ["raghuinstech.com", "raghuenggcollege.in"]

        if not email:
            raise ValidationError("Email is required.")

        domain = email.split("@")[-1]
        if domain not in allowed_domains:
            raise ValidationError("❌ Only official college emails are allowed (raghuinstech.com / raghuenggcollege.in).")

        if User.objects.filter(email=email).exists():
            raise ValidationError("⚠️ This email is already registered.")
        return email

    def save(self, commit=True):
        # 1. Save the User object first
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            
            # 2. Save the UserProfile object
            # The signal (post_save) in models.py creates the profile, 
            # so we only need to update it here.
            UserProfile.objects.filter(user=user).update(
                phone_number=self.cleaned_data.get('phone_number')
            )
            
        return user


class LostItemForm(forms.ModelForm):
    class Meta:
        model = LostItem
        fields = ['name', 'description', 'features', 'photo']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600',
                'placeholder': 'e.g., iPhone 13, Backpack, Keys'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600',
                'placeholder': 'Describe your lost item in detail...',
                'rows': 3
            }),
            'features': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-600',
                'placeholder': 'Any unique features, scratches, stickers, or identifying marks...',
                'rows': 3
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'hidden',  # hide default input, we will use custom area
                'id': 'photoInput'
            }),
        }


class FoundItemForm(forms.ModelForm):
    class Meta:
        model = FoundItem
        fields = ['name', 'description', 'features', 'photo']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-600',
                'placeholder': 'e.g., iPhone 13, Backpack, Keys'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-600',
                'placeholder': 'Describe the found item in detail...',
                'rows': 3
            }),
            'features': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-600',
                'placeholder': 'Any unique features, scratches, stickers, or identifying marks...',
                'rows': 3
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'hidden',
                'id': 'photoInput',
                'required': 'required'   # Make it mandatory
            }),
        }
