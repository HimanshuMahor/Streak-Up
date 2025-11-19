from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _  # For translation-ready strings

class UserManager(BaseUserManager):
    """Custom manager for the User model with email as the username field."""

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))  # Translation-ready
        email = self.normalize_email(email)
        
        # Ensure username is handled if not provided
        if 'username' not in extra_fields:
            # Option 1: Use part of email as default username
            extra_fields['username'] = email.split('@')[0]
            # Option 2: OR raise error if username is required
            # raise ValueError(_("The Username must be set"))
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        # Validate that the superuser has correct flags
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email):
        """Allow users to log in with their email address."""
        return self.get(email=email)