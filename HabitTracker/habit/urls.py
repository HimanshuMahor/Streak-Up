from django.urls import path
from . import views

app_name = 'habit'

urlpatterns = [

    # -----------------------------
    # DASHBOARD / INDEX
    # -----------------------------
    path('', views.dashboard, name='dashboard'),  # Homepage
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),

    # -----------------------------
    # AUTHENTICATION / PASSWORD
    # -----------------------------
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('register/', views.register, name='register'),
    path('password/change/', views.password_change, name='password_change'),
    path('password/reset/', views.password_reset_request, name='password_reset'),
    path('password/reset/done/', views.password_reset_done, name='password_reset_done'),
    path('password/reset/confirm/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password/reset/complete/', views.password_reset_complete, name='password_reset_complete'),

    # -----------------------------
    # FRIENDS / SOCIAL
    # -----------------------------
    path('friends/', views.friends, name='friends'),
    path('friends/add/', views.friend_request_send, name='friend_request_send'),
    path('friends/accept/<int:pk>/', views.friend_request_accept, name='friend_request_accept'),
    path('friends/reject/<int:pk>/', views.friend_request_reject, name='friend_request_reject'),
    path('friends/remove/<int:pk>/', views.friend_remove, name='friend_remove'),

    # -----------------------------
    # NOTIFICATIONS
    # -----------------------------
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-read/<int:pk>/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/mark-all-read/', views.notification_mark_all_read, name='notification_mark_all_read'),
    path('notifications/delete/<int:pk>/', views.notification_delete, name='notification_delete'),

    # -----------------------------
    # REWARDS
    # -----------------------------
    path('rewards/', views.rewards, name='rewards'),
    path('rewards/add/', views.reward_add, name='reward_add'),
    path('rewards/claim/<int:pk>/', views.reward_claim, name='reward_claim'),

    # -----------------------------
    # STREAKS / HABITS
    # -----------------------------
    path('streaks/', views.streaks, name='streaks'),
    path('habit/add/', views.habit_add, name='habit_add'),
    path('habits/', views.habit_list, name='habit_list'),
    path('habit/<int:pk>/', views.habit_detail, name='habit_detail'),
    path('habit/<str:st>/', views.habit_list, name='habit_filter'),
    path('habit/create/', views.habit_create, name='habit_create'),
    path('habit/<int:pk>/edit/', views.habit_edit, name='habit_edit'),
    path('habit/<int:pk>/delete/', views.habit_delete, name='habit_delete'),

    # -----------------------------
    # Challenge
    # -----------------------------
    path('challenges/', views.challenge_list, name='challenge_list'),
    path('challenge/create/', views.challenge_create, name='challenge_create'),
    path('challenge/<int:pk>/', views.challenge_detail, name='challenge_detail'),
    path('challenge/<int:pk>/edit/', views.challenge_edit, name='challenge_edit'),
    path('challenge/<int:pk>/delete/', views.challenge_delete, name='challenge_delete'),

    # -----------------------------
    # HABIT LOGS
    # -----------------------------
    path('logs/', views.log_list, name='log_list'),
    path('logs/add/', views.log_add, name='log_add'),
    path("logs/add/<int:habit_id>/", views.log_add, name="log_add"),
    path("log/<int:pk>/edit/", views.log_edit, name="log_edit"),


]
