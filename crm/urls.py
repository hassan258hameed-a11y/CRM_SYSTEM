from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    path("dashboard/stats/", views.dashboard_stats, name="dashboard_stats"),

    # ✅ Public apply URL (for Facebook ads etc.)
    # This simply reuses your existing "Add Student" form.
    path(
        "apply/",
        RedirectView.as_view(pattern_name="student_create", permanent=False),
        name="apply",
    ),

    # Students
    path("students/", views.students_list, name="students_list"),
    path("students/add/", views.student_create, name="student_create"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),

    # Leads
    path("leads/", views.leads_list, name="leads_list"),

    # Webhook for Facebook / other sources to create leads
    path("webhook/lead/", views.webhook_lead, name="webhook_lead"),

    # Users
    path("users/", views.manage_users, name="manage_users"),
    path("users/<int:pk>/", views.user_detail, name="user_detail"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),

    # Applications
    path("applications/", views.applications_list, name="applications_list"),
    path(
        "applications/update-status/",
        views.application_update_status,
        name="application_update_status",
    ),

    # Email integration
    path("email/", views.email_integration, name="email_integration"),
    path("email/broadcast/", views.email_broadcast, name="email_broadcast"),
    path("email/send/<int:pk>/", views.student_send_email, name="student_send_email"),

    # Facebook integration page
    path("facebook/", views.facebook_integration, name="facebook_integration"),
]
