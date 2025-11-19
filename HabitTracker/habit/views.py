from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import HttpResponseRedirect, HttpResponse
from django.db.models import Q
from django import forms
from django.utils.timezone import now
import datetime

from .models import (
    User, Habit, Streak, Reward, Badge, Friendship,
    FriendRequest, Notification, Challenge, HabitLog
)
from .forms import (
    UserLoginForm, PasswordChangeForm, PasswordResetForm,UserRegisterForm,UserProfileForm,
    SetPasswordForm, HabitForm, RewardForm, FriendRequestForm, ChallengeForm, HabitLogForm,
)

# -----------------------------
# DASHBOARD
# -----------------------------
def dashboard(request):
    """
    Render the main dashboard page as the homepage.
    Include stats like habits, streaks, rewards summary, etc.
    """
    if request.user.is_authenticated:

        current_user = request.user
        # Example context, adapt according to your models
        context = {
            'total_habits': Habit.objects.filter(user=current_user).count(),
            'habits': Habit.objects.filter(user=current_user).filter(status='progressing'),
            'active_streaks': Streak.objects.filter(user=current_user, is_active=True).count(),
            'total_points': current_user.points,
            'recent_logs': HabitLog.objects.all().order_by('-date')[:5],
            'rewards': Reward.objects.filter(user=current_user),
            'today': today_date()
        }
        return render(request, 'habit/dashboard.html', context)
    
    return redirect('habit:login')
 

# -----------------------------
# AUTHENTICATION / PASSWORD VIEWS
# -----------------------------
def custom_login(request):
    if request.user.is_authenticated:
        return redirect('habit:dashboard')
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('habit:dashboard')
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = UserLoginForm()
    return render(request, 'habit/auth/login.html', {'form': form})

@login_required
def custom_logout(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('habit:login')


@login_required
def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated successfully.")
            return redirect('habit:streaks')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'habit/auth/password_change.html', {'form': form})

def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(request=request, 
                      use_https=request.is_secure(),
                      email_template_name='habit/auth/password_reset_email.html')
            return redirect('habit:password_reset_done')
    else:
        form = PasswordResetForm()
    return render(request, 'habit/auth/password_reset.html', {'form': form})

def password_reset_done(request):
    return render(request, 'habit/auth/password_reset_done.html')

def password_reset_confirm(request, uidb64, token):
    from django.contrib.auth.views import PasswordResetConfirmView
    # Using Django's default view internally
    view = PasswordResetConfirmView.as_view(
        template_name='habit/auth/password_reset_confirm.html',
        success_url=reverse_lazy('habit:password_reset_complete')
    )
    return view(request, uidb64=uidb64, token=token)

def password_reset_complete(request):
    return render(request, 'habit/auth/password_reset_complete.html')

def register(request):
    if request.user.is_authenticated:
        return redirect('habit:dashboard')
    
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect('habit:dashboard')
    else:
        form = UserRegisterForm()
    
    return render(request, 'habit/auth/registration.html', {'form': form})


# -----------------------------
# FRIENDS / SOCIAL VIEWS
# -----------------------------
@login_required
def friends(request):
    friends = Friendship.objects.filter(user=request.user)
    friend_requests = FriendRequest.objects.filter(to_user=request.user)
    return render(request, 'habit/friends.html', {
        'friends': friends,
        'friend_requests': friend_requests
    })

@login_required
def friend_request_send(request):
    if request.method == 'POST':
        form = FriendRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                to_user = User.objects.get(email=email)
                if to_user != request.user:
                    FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
                    messages.success(request, f"Friend request sent to {to_user.username}")
                else:
                    messages.error(request, "You cannot send a request to yourself.")
            except User.DoesNotExist:
                messages.error(request, "User with this email does not exist.")
            return redirect('habit:friends')
    else:
        form = FriendRequestForm()
    return render(request, 'habit/friends.html', {'form': form})

@login_required
def friend_request_accept(request, pk):
    fr = get_object_or_404(FriendRequest, pk=pk, to_user=request.user)
    Friendship.objects.get_or_create(user=request.user, friend=fr.from_user)
    Friendship.objects.get_or_create(user=fr.from_user, friend=request.user)
    fr.delete()
    messages.success(request, f"You are now friends with {fr.from_user.username}")
    return redirect('habit:friends')

@login_required
def friend_request_reject(request, pk):
    fr = get_object_or_404(FriendRequest, pk=pk, to_user=request.user)
    fr.delete()
    messages.info(request, f"Friend request from {fr.from_user.username} rejected")
    return redirect('habit:friends')

@login_required
def friend_remove(request, pk):
    friendship = get_object_or_404(Friendship, pk=pk, user=request.user)
    friendship.friendship_reverse().delete()  # Remove both sides
    friendship.delete()
    messages.info(request, f"{friendship.friend.username} removed from friends")
    return redirect('habit:friends')


# -----------------------------
# NOTIFICATIONS VIEWS
# -----------------------------
@login_required
def notifications(request):
    notifications_list = Notification.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(notifications_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    unread_count = notifications_list.filter(is_read=False).count()
    return render(request, 'habit/notifications.html', {
        'notifications': page_obj,
        'unread_count': unread_count
    })

@login_required
def notification_mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    return redirect('habit:notifications')

@login_required
def notification_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('habit:notifications')

@login_required
def notification_delete(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.delete()
    return redirect('habit:notifications')


# -----------------------------
# REWARDS VIEWS
# -----------------------------
@login_required
def rewards(request):
    available_rewards_list = Reward.objects.filter(active=True).order_by('points_required')
    claimed_rewards_list = Reward.objects.filter(claimed_by=request.user).order_by('-claimed_at')
    badges = Badge.objects.all()
    user_badges = request.user.badges.all()
    return render(request, 'habit/rewards.html', {
        'available_rewards_list': available_rewards_list,
        'claimed_rewards_list': claimed_rewards_list,
        'badges': badges,
        'user_badges': user_badges,
        'user': request.user,
        'total_rewards': Reward.objects.count(),
        'claimed_rewards': claimed_rewards_list.count(),
        'available_rewards': available_rewards_list.count(),
        'total_points_spent': claimed_rewards_list.aggregate(total=models.Sum('points_required'))['total'] or 0
    })

@login_required
def reward_add(request):
    if request.method == 'POST':
        form = RewardForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Reward created successfully!")
            return redirect('habit:rewards')
    else:
        form = RewardForm()
    return render(request, 'habit/reward_add.html', {'form': form})

@login_required
def reward_claim(request, pk):
    reward = get_object_or_404(Reward, pk=pk)
    if request.user.points >= reward.points_required:
        request.user.points -= reward.points_required
        request.user.save()
        reward.claimed_by.add(request.user)
        messages.success(request, f"You claimed {reward.title}!")
    else:
        messages.error(request, "Not enough points to claim this reward.")
    return redirect('habit:rewards')


# -----------------------------
# STREAKS / HABITS VIEWS
# -----------------------------
@login_required
def streaks(request):
    streaks_list = Streak.objects.filter(user=request.user).order_by('-current_streak')
    total_current_streak = sum(s.current_streak for s in streaks_list)
    max_streak = max((s.longest_streak for s in streaks_list), default=0)
    active_streaks = streaks_list.filter(is_active=True).count()
    completion_rate = int((active_streaks / streaks_list.count()) * 100) if streaks_list else 0
    return render(request, 'habit/streaks.html', {
        'streaks': streaks_list,
        'total_current_streak': total_current_streak,
        'max_streak': max_streak,
        'active_streaks': active_streaks,
        'completion_rate': completion_rate
    })



# ==========================
# Habit
# ==========================


@login_required
def habit_add(request):
    if request.method == 'POST':
        form = HabitForm(request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            messages.success(request, "Habit created successfully!")
            return redirect('habit:streaks')
    else:
        form = HabitForm()
    return render(request, 'habit/habits/habit_add.html', {'form': form})

@login_required
def habit_create(request):
    if request.method == "POST":
        form = HabitForm(request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.save()
            messages.success(request, "Habit created successfully!")
            return redirect('habit:habit_list')
    else:
        form = HabitForm()
    return render(request, 'habit/habits/habit_add.html', {'form': form})


@login_required
def habit_list(request, st = "all"):
    habits = Habit.objects.filter(user=request.user)
    if st == "all":
        pass
    elif st == "active":
        habits = habits.filter(status="progressing")
    elif st == "failed":
        habits = habits.filter(status="failed")
    elif st == "achieved":
        habits = habits.filter(status="achieved")
    return render(request, 'habit/habits/habit_list.html', {'habits': habits, 'filter':st})

@login_required
def habit_detail(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    streaks = Streak.objects.filter(habit=habit)
    return render(request, 'habit/habits/habit_detail.html', {'habit': habit, 'streaks': streaks, 'today':today_date()})


@login_required
def habit_edit(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == "POST":
        form = HabitForm(request.POST, instance=habit)
        if form.is_valid():
            form.save()
            messages.success(request, "Habit updated successfully!")
            return redirect('habit:habit_detail', pk=habit.pk)
    else:
        form = HabitForm(instance=habit)
    return render(request, 'habit/habits/habit_add.html', {'form': form})

@login_required
def habit_delete(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    if request.method == "POST":
        habit.delete()
        messages.success(request, "Habit deleted successfully!")
        return redirect('habit:habit_list')
    return render(request, 'habit/habits/habit_confirm_delete.html', {'habit': habit})

# ==========================
# Challenge
# ==========================
@login_required
def challenge_list(request):
    current_user = User.objects.get(email = request.user.email)
    # my_challenges = current_user.challenges.all()
    my_challenges = Challenge.objects.all()
    all_challenges = Challenge.objects.all()
    return render(request, 'habit/challenges/challenge_list.html', {'my_challenges': my_challenges, 'all_challenges': all_challenges})

@login_required
def challenge_detail(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk, user=request.user)
    return render(request, 'habit/challenges/challenge_detail.html', {'challenge': challenge})

@login_required
def challenge_create(request):
    if request.method == "POST":
        form = ChallengeForm(request.POST)
        if form.is_valid():
            challenge = form.save(commit=False)
            challenge.created_by = request.user 
            challenge.save()
            messages.success(request, "Challenge created successfully!")
            return redirect('habit:challenge_list')
    else:
        form = ChallengeForm()
    return render(request, 'habit/challenges/challenge_form.html', {'form': form})



@login_required
def challenge_edit(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk, user=request.user)
    if request.method == "POST":
        form = ChallengeForm(request.POST, instance=challenge)
        if form.is_valid():
            form.save()
            messages.success(request, "Challenge updated successfully!")
            return redirect('habit:challenge_detail', pk=challenge.pk)
    else:
        form = ChallengeForm(instance=challenge)
    return render(request, 'habit/challenge_form.html', {'form': form})

@login_required
def challenge_delete(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk, user=request.user)
    if request.method == "POST":
        challenge.delete()
        messages.success(request, "Challenge deleted successfully!")
        return redirect('habit:challenge_list')
    return render(request, 'habit/challenge_confirm_delete.html', {'challenge': challenge})

# ==========================
# Profile View
# ==========================
@login_required
def profile(request):
    return render(request, 'habit/profile/profile.html')

@login_required
def edit_profile(request):
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('habit:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'habit/profile/edit_profile.html', {'form': form})

# -----------------------------
# HABIT LOGS
# -----------------------------

@login_required
def log_edit(request, pk):
    log = get_object_or_404(HabitLog, pk=pk, habit__user=request.user)
    if request.method == "POST":
        form = HabitLogForm(request.POST, instance=log)
        if form.is_valid():
            log = form.save(commit=False)
            log.habit = log.habit  # Force assign to the clicked habit
            log.save()
            return redirect("habit:habit_detail", pk=log.habit.pk)  # back to habit detail
        else:
            messages.error(request, "Invalid Input")
    else:
        form = HabitLogForm(habit=log.habit,instance=log)

    form.fields['habit'].widget = forms.HiddenInput()
    form.initial['habit'] = log.habit
    
    form.fields['date'].widget = forms.HiddenInput()
    form.initial['date'] = datetime.date.today()

    form.fields['status'].widget = forms.HiddenInput()
    form.initial['status'] = 'pending'
    
    return render(request, "habit/logs/log_form.html", {"habit":log.habit,"today":today_date(),"form": form, "title": "Edit Log"})

def log_list(request):
    """
    Show all habit logs for the logged-in user.
    """
    logs = HabitLog.objects.filter(habit__user=request.user).order_by('-date')
    return render(request, 'habit/logs/log.html', {'logs': logs, "today":today_date()})


def log_add(request, habit_id):
    """
    Add a log for a specific habit, habit field fixed to the selected habit.
    """
    habit = get_object_or_404(Habit, id=habit_id, user=request.user)
    try:
        log_exist = HabitLog.objects.get(habit=habit, date=today_date())
        return redirect("habit:log_edit", pk=log_exist.id)
    except HabitLog.DoesNotExist:
        pass
        

    if request.method == "POST":
        form = HabitLogForm(request.POST, habit=habit)
        if form.is_valid():
            log = form.save(commit=False)
            log.habit = habit  # Force assign to the clicked habit
            log.save()
            return redirect("habit:log_list")
        else:
            messages.error(request, "Invalid Input")
    else:
        form = HabitLogForm(habit=habit)

    # Hide habit field in template (we'll show it as plain text instead)
    form.fields['habit'].widget = forms.HiddenInput()
    form.initial['habit'] = habit
    
    form.fields['date'].widget = forms.HiddenInput()
    form.initial['date'] = datetime.date.today()

    form.fields['status'].widget = forms.HiddenInput()
    form.initial['status'] = 'pending'

    return render(request, "habit/logs/log_add.html", {"form": form, "habit": habit, "today": today_date()})

# Utility Functions

def today_date():
    return now().date()


