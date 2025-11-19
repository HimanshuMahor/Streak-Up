from django import forms
from django.db import models
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm
)
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import User, Habit, HabitLog, Challenge, FriendRequest, Reward, Category

# 🔑 User Registration Form
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        "class": "form-control", "placeholder": "Email"
    }))
    username = forms.CharField(required=True, widget=forms.TextInput(attrs={
        "class": "form-control", "placeholder": "Username"
    }))
    nickname = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "class": "form-control", "placeholder": "Nickname"
    }))
    contact = forms.CharField(required=False, widget=forms.TextInput(attrs={
        "class": "form-control", "placeholder": "Contact"
    }))
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control", "placeholder": "Password"
        }),
        help_text="Your password must contain at least 8 characters."
    )
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "Confirm Password"
    }))

    class Meta:
        model = User
        fields = ["email", "username","nickname","contact", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_("A user with this email already exists."))
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError(_("This username is already taken."))
        return username


# 🔑 Login Form
class UserLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control", "placeholder": "Email", "autofocus": True
        })
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "Password"
    }))


# 🔑 Profile Update Form

class UserProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ["username",'email', "avatar", "bio" , 'nickname', 'contact']
        widgets = {
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Tell us about yourself..."}),
            "nickname": forms.TextInput(attrs={"class": "form-control"}),
            "contact": forms.NumberInput(attrs={"class": "form-control"})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})

    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Check if username is taken by another user
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError(_("This username is already taken."))
        return username

# 📋 Habit Form
class HabitForm(forms.ModelForm):
    class Meta:
        model = Habit
        fields = [
            "name", "category", "description", "frequency",
            "custom_days", "time_of_day", "target_per_day", "unit", "start_date", "end_date"
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Drink Water"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional description..."}),
            "frequency": forms.Select(attrs={"class": "form-select"}),
            "custom_days": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": 'e.g., ["Mon", "Wed", "Fri"]'
            }),
            "time_of_day": forms.Select(attrs={"class": "form-select"}),
            "target_per_day": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "max": "99999"
            }),
            "unit": forms.Select(attrs={"class":"form-select"}),
            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
        }
        help_texts = {
            "custom_days": "Required only if frequency is 'Custom Days'. Format: ['Mon','Wed','Fri']",
            "target_per_day": "How many times you want to complete this habit per day",
        }

    def clean(self):
        cleaned_data = super().clean()
        frequency = cleaned_data.get('frequency')
        custom_days = cleaned_data.get('custom_days')
        end_date = cleaned_data.get('end_date')
        start_date = cleaned_data.get('start_date')

        # Validate custom_days for custom frequency
        if frequency == 'custom' and not custom_days:
            raise ValidationError({
                'custom_days': _("Custom days are required for custom frequency.")
            })

        # Validate date range
        if end_date and start_date and end_date < start_date:
            raise ValidationError({
                'end_date': _("End date cannot be before start date.")
            })

        return cleaned_data

    def clean_target_per_day(self):
        target = self.cleaned_data.get('target_per_day')
        if target < 1:
            raise ValidationError(_("Target must be at least 1."))
        if target > 99999:
            raise ValidationError(_("Target cannot exceed 99999."))
        return target

# ✅ Habit Log Form
# class LogForm(forms.ModelForm):
#     class Meta:
#         model = HabitLog
#         fields = ["date", "status", "notes"]

class HabitLogForm(forms.ModelForm):
    class Meta:
        model = HabitLog
        fields = ['habit', 'date', 'status','progress']
        widgets = {
            "progress": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "max": "99999"  # You might want to make this dynamic based on habit.target
            }),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.habit = kwargs.pop('habit', None)
        super().__init__(*args, **kwargs)
        if self.habit:
            self.fields['progress'].widget.attrs['max'] = self.habit.target_per_day

    def clean_progress(self):
        progress = self.cleaned_data.get('progress')
        if self.habit and progress > self.habit.target_per_day:
            raise ValidationError(
                _("Progress cannot exceed the daily target of %(target)s.") %
                {'target': self.habit.target_per_day}
            )
        return progress


# 🏆 Challenge Form
class ChallengeForm(forms.ModelForm):

    class Meta:
        model = Challenge
        fields = ["name", "description", "start_date", "end_date"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "30-Day Fitness Challenge"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
                "min": timezone.now().date().isoformat()
            }),
            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
                "min": timezone.now().date().isoformat()
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError(_("End date must be after start date."))
            if start_date < timezone.now().date():
                raise ValidationError(_("Start date cannot be in the past."))

        return cleaned_data
    
    
    


# 👥 Friend Request Form
class FriendRequestForm(forms.ModelForm):
    # Use Email instead of dropdown for better UX
    to_user_email = forms.EmailField(
        label="Friend's Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Enter your friend's email"
        })
    )

    class Meta:
        model = FriendRequest
        fields = []  # We're using to_user_email instead

    def clean_to_user_email(self):
        email = self.cleaned_data.get('to_user_email')
        try:
            to_user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError(_("No user found with this email address."))
        
        # Check if they're trying to add themselves
        if self.instance and to_user == self.instance.from_user:
            raise ValidationError(_("You cannot send a friend request to yourself."))
        
        return to_user


# 🎁 Reward Form (for creating rewards)
class RewardForm(forms.ModelForm):
    class Meta:
        model = Reward
        fields = ["title", "description", "points_required"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Movie Night"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "points_required": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1"
            }),
        }


# 🔑 Password Management Forms (unchanged, they're good!)
class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "Old Password"
    }))
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "New Password"
    }))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "Confirm New Password"
    }))


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        "class": "form-control", "placeholder": "Enter your email"
    }))


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "New Password"
    }))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        "class": "form-control", "placeholder": "Confirm Password"
    }))


