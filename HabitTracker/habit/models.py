from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings  # Import settings to reference AUTH_USER_MODEL
import datetime
from django.utils.timezone import now

from .manager import UserManager

class UnitType(models.Model):
    name = models.CharField(max_length=20,unique=True)

    def __str__(self):
        return self.name

class Unit(models.Model):
    name = models.CharField(max_length=20, unique=True)
    type = models.ForeignKey(UnitType, on_delete=models.SET_NULL, null=True, blank=True)
    symbol = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.name

# -----------------------
# 1. Custom User Model
# -----------------------
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, max_length=255)
    username = models.CharField(max_length=50, unique=True)
    nickname = models.CharField(max_length=50, blank=True, null=True)
    contact = models.CharField(max_length=12, blank=True, null=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    user_timezone = models.CharField(max_length=50, default="UTC")
    bio = models.TextField(blank=True, null=True)
    points = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def save(self, *args, **kwargs):
        # Auto-set completion status based on progress
        self.contact = None if self.contact is "" else self.contact
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email

# -----------------------
# 2. Habit & Category
# -----------------------
class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Habit(models.Model):
    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("custom", "Custom Days"),
    ]

    TIME_OF_DAY = [
        ("morning","Morning"),
        ("afternoon","Afternoon"),
        ("evening","Evening"),
        ("anytime","Anytime")
    ]

    STATUS = [
        ("achieved","Achieved"),
        ("failed","Failed"),
        ('progressing',"Progressing")
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="habits")
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default="daily")
    time_of_day = models.CharField(max_length=20, choices=TIME_OF_DAY, default="anytime")
    custom_days = models.JSONField(blank=True, null=True)  # e.g., {"days": ["Mon", "Wed", "Fri"]}
    target_per_day = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(99999)]  # Prevents unrealistic targets
    )
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS, default="progressing")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(blank=True, null=True)

    class Meta:
        # Index on user and active status for faster filtering
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

   

    def clean(self):
        # Validate date logic
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError({'end_date': 'End date cannot be before the start date.'})
        # Validate custom_days if frequency is 'custom'
        if self.frequency == 'custom' and (not self.custom_days or not self.custom_days.get('days')):
            raise ValidationError({'custom_days': 'Custom frequency requires a list of days.'})

    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation on every save
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username}: {self.name}"


# -----------------------
# 3. Habit Logging
# -----------------------
class HabitLog(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("done", "Done"),
    ]

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="logs")
    date = models.DateField(default=timezone.now)
    progress = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    class Meta:
        # Index on date for faster queries on logs by date
        
        unique_together = ('habit', 'date')
        indexes = [
            models.Index(fields=['date']),
        ]
        verbose_name_plural = "Habit Logs"

    def completion_percentage(self):
        return (self.progress / self.habit.target_per_day)*100
    
    def completion_value(self):
        return round((self.progress / self.habit.target_per_day)*100,2)
    
    def find_day(self):
        return self.date.strftime("%A")

    def clean(self):
        # Ensure progress doesn't exceed the habit's target
        if self.progress > self.habit.target_per_day:
            raise ValidationError(
                {'progress': f'Progress cannot exceed the daily target of {self.habit.target_per_day}.'}
            )

    def save(self, *args, **kwargs):
        # Auto-set completion status based on progress
        self.completed = (self.progress >= self.habit.target_per_day)
        self.status = 'done' if self.completed else 'pending'
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.habit.name} - {self.date} ({self.status})"


# -----------------------
# 4. Streaks & Rewards
# -----------------------
class Streak(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="streaks")  
    habit = models.ForeignKey("Habit", on_delete=models.CASCADE, related_name="streaks")
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    longest_streak = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)  # ✅ New field

    last_completed = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Streaks"

    def __str__(self):
        return f"{self.user.username} - {self.habit.name} (Current: {self.current_streak}, Longest: {self.longest_streak})"


class Badge(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    points_required = models.PositiveIntegerField(validators=[MinValueValidator(0)])

    class Meta:
        verbose_name_plural = "Badges"

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")
        verbose_name_plural = "User Badges"

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


# -----------------------
# 5. Notifications & Reminders
# -----------------------
class Reminder(models.Model):
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="reminders")
    time = models.TimeField(help_text="Daily reminder time")  # Use a TimeField for clock time
    message = models.CharField(max_length=200, default="Time to complete your habit!")

    class Meta:
        verbose_name_plural = "Reminders"

    def __str__(self):
        return f"Reminder for {self.habit.name} at {self.time}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),  # Speeds up common queries
        ]
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}..."


# -----------------------
# 6. Social Features
# -----------------------
class Friendship(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friends")
    friend = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friend_of")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "friend")
        verbose_name_plural = "Friendships"

    def __str__(self):
        return f"{self.user.username} is friends with {self.friend.username}"

    def clean(self):
        # Prevent user from being friends with themselves
        if self.user == self.friend:
            raise ValidationError("Users cannot be friends with themselves.")


class FriendRequest(models.Model):
    from_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_requests', on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("from_user", "to_user")
        ordering = ["-timestamp"]
        verbose_name_plural = "Friend Requests"

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} ({'Accepted' if self.is_accepted else 'Pending'})"

    def clean(self):
        # Prevent self-requests
        if self.from_user == self.to_user:
            raise ValidationError("You cannot send a friend request to yourself.")
        # Check if a friendship or request already exists
        if Friendship.objects.filter(user=self.from_user, friend=self.to_user).exists():
            raise ValidationError("A friendship already exists.")


class Challenge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_challenges")
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="challenges")

    class Meta:
        verbose_name_plural = "Challenges"

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError({'end_date': 'End date must be after the start date.'})

    def __str__(self):
        return self.name


class ChallengeProgress(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="progress")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    progress = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],  # Ensure progress is a percentage
        help_text="Percentage completion (0-100)"
    )
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("challenge", "user")
        verbose_name_plural = "Challenge Progresses"

    def __str__(self):
        return f"{self.user.username} - {self.challenge.name}: {self.progress}%"


# -----------------------
# 7. Reward
# -----------------------
class Reward(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='rewards', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    points_required = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    is_claimed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Rewards"

    def __str__(self):
        return f"{self.title} ({self.user.username})"
    



def today_date():
    return now().date()