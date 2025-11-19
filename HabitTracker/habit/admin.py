from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models import Count, Avg
from .models import *

# -------------------------
# Customize Django Admin
# -------------------------
admin.site.site_header = "Habit Tracker Admin"
admin.site.site_title = "Habit Tracker Administration"
admin.site.index_title = "Dashboard Administration"


# -------------------------
# Inline Admin Classes
# -------------------------
class HabitInline(admin.TabularInline):
    model = Habit
    extra = 0
    fields = ("name", "frequency", "is_active", "created_at")
    readonly_fields = ("created_at",)
    can_delete = False
    show_change_link = True

class NotificationInline(admin.TabularInline):
    model = Notification
    extra = 0
    fields = ("message", "is_read", "created_at")
    readonly_fields = ("created_at",)
    can_delete = False

# -------------------------
# Custom User Admin
# -------------------------
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "username", "habit_count", "current_points", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_superuser", "is_active", "date_joined"]
    list_select_related = True
    readonly_fields = ("date_joined", "last_login", "avatar_preview")
    inlines = [HabitInline, NotificationInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("username", "avatar", "avatar_preview", "user_timezone", "bio", "points")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "password1", "password2", "is_staff", "is_active"),
        }),
    )

    search_fields = ("email", "username")
    actions = ["activate_users", "deactivate_users"]

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.avatar.url)
        return "No Avatar"
    avatar_preview.short_description = "Avatar Preview"

    def habit_count(self, obj):
        return obj.habits.count()
    habit_count.short_description = "Habits"
    habit_count.admin_order_field = "habits__count"

    def current_points(self, obj):
        return obj.points
    current_points.short_description = "Points"
    current_points.admin_order_field = "points"

    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} users were activated.")
    activate_users.short_description = "Activate selected users"

    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} users were deactivated.")
    deactivate_users.short_description = "Deactivate selected users"

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            habits_count=Count('habits')
        )


# -------------------------
# Habit and Related Admins
# -------------------------
class HabitLogInline(admin.TabularInline):
    model = HabitLog
    extra = 0
    fields = ("date", "progress", "completed", "status")
    readonly_fields = ("date",)
    can_delete = False
    max_num = 7  # Show only last 7 logs

@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("name", "user_email", "category", "frequency", "log_count", "is_active", "created_at")
    list_filter = ("frequency", "is_active", "category", "created_at")
    search_fields = ("name", "user__email", "user__username")
    list_select_related = ("user", "category")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "current_streak_display")
    inlines = [HabitLogInline]
    actions = ["activate_habits", "deactivate_habits"]

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "User Email"
    user_email.admin_order_field = "user__email"

    def log_count(self, obj):
        return obj.logs.count()
    log_count.short_description = "Logs"
    log_count.admin_order_field = "logs__count"

    def current_streak_display(self, obj):
        if hasattr(obj, 'streak'):
            return f"{obj.streak.current_streak} days (Best: {obj.streak.longest_streak})"
        return "No streak data"
    current_streak_display.short_description = "Current Streak"

    def activate_habits(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} habits were activated.")
    activate_habits.short_description = "Activate selected habits"

    def deactivate_habits(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} habits were deactivated.")
    deactivate_habits.short_description = "Deactivate selected habits"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'category'
        ).prefetch_related(
            'logs'
        ).annotate(
            logs_count=Count('logs')
        )


@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ("habit_name", "user_email", "date", "progress_display", "completed", "status")
    list_filter = ("habit","completed", "status", "date")
    search_fields = ("habit__name", "habit__user__email")
    list_select_related = ("habit__user",)
    date_hierarchy = "date"
    readonly_fields = ("date",)

    def habit_name(self, obj):
        return obj.habit.name
    habit_name.short_description = "Habit"
    habit_name.admin_order_field = "habit__name"

    def user_email(self, obj):
        return obj.habit.user.email
    user_email.short_description = "User"
    user_email.admin_order_field = "habit__user__email"

    def progress_display(self, obj):
        return f"{obj.progress}/{obj.habit.target_per_day}"
    progress_display.short_description = "Progress"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'habit', 'habit__user'
        )


# -------------------------
# Other Model Admins
# -------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "habit_count", "description")
    search_fields = ("name",)
    list_per_page = 20

    def habit_count(self, obj):
        return obj.habit_set.count()
    habit_count.short_description = "Habits"

@admin.register(UnitType)
class UnitTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    list_per_page = 20

    def habit_count(self, obj):
        return obj.habit_set.count()
    habit_count.short_description = "Habits"

@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "symbol")
    search_fields = ("name",)
    list_per_page = 20

    def habit_count(self, obj):
        return obj.habit_set.count()
    habit_count.short_description = "Habits"


@admin.register(Streak)
class StreakAdmin(admin.ModelAdmin):
    list_display = ("habit", "current_streak", "longest_streak", "last_completed")
    list_select_related = ("habit",)
    search_fields = ("habit__name", "habit__user__email")


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("name", "points_required", "user_count")
    search_fields = ("name",)
    list_filter = ("points_required",)

    def user_count(self, obj):
        return obj.userbadge_set.count()
    user_count.short_description = "Users Earned"


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "awarded_at")
    list_filter = ("awarded_at", "badge")
    list_select_related = ("user", "badge")
    search_fields = ("user__email", "badge__name")
    readonly_fields = ("awarded_at",)


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ("habit", "time", "message")
    list_select_related = ("habit",)
    search_fields = ("habit__name", "message")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message_preview", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__email", "message")
    list_select_related = ("user",)
    readonly_fields = ("created_at",)
    actions = ["mark_as_read", "mark_as_unread"]

    def message_preview(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    message_preview.short_description = "Message"

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notifications marked as read.")
    mark_as_read.short_description = "Mark as read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} notifications marked as unread.")
    mark_as_unread.short_description = "Mark as unread"


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("user", "friend", "created_at")
    search_fields = ("user__email", "friend__email")
    list_select_related = ("user", "friend")
    readonly_fields = ("created_at",)


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "created_by", "participant_count")
    list_filter = ("start_date", "end_date")
    search_fields = ("name", "created_by__email")
    list_select_related = ("created_by",)
    filter_horizontal = ("participants",)

    def participant_count(self, obj):
        return obj.participants.count()
    participant_count.short_description = "Participants"


@admin.register(ChallengeProgress)
class ChallengeProgressAdmin(admin.ModelAdmin):
    list_display = ("challenge", "user", "progress", "completed")
    list_filter = ("completed", "challenge")
    search_fields = ("challenge__name", "user__email")
    list_select_related = ("challenge", "user")


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "is_accepted", "timestamp")
    list_filter = ("is_accepted", "timestamp")
    search_fields = ("from_user__email", "to_user__email")
    list_select_related = ("from_user", "to_user")
    readonly_fields = ("timestamp",)


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "points_required", "is_claimed", "created_at")
    list_filter = ("is_claimed", "created_at")
    search_fields = ("title", "user__email")
    list_select_related = ("user",)
    readonly_fields = ("created_at",)
    actions = ["mark_as_claimed", "mark_as_unclaimed"]

    def mark_as_claimed(self, request, queryset):
        updated = queryset.update(is_claimed=True)
        self.message_user(request, f"{updated} rewards marked as claimed.")
    mark_as_claimed.short_description = "Mark as claimed"

    def mark_as_unclaimed(self, request, queryset):
        updated = queryset.update(is_claimed=False)
        self.message_user(request, f"{updated} rewards marked as unclaimed.")
    mark_as_unclaimed.short_description = "Mark as unclaimed"


# Finally register the custom User
admin.site.register(User, UserAdmin)