from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# ----------------------------------------------------
# COUNTRY
# ----------------------------------------------------
class Country(models.Model):
    name = models.CharField(max_length=128, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


# ----------------------------------------------------
# TAGS
# ----------------------------------------------------
class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)

    def __str__(self):
        return self.name


# ----------------------------------------------------
# STUDENT
# ----------------------------------------------------
class Student(models.Model):

    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    )

    APPLICATION_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    # BASIC INFO
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)

    age = models.PositiveIntegerField(null=True, blank=True)

    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    enrollment_date = models.DateField(blank=True, null=True)

    # CONTACT
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    # PASSPORT
    passport_number = models.CharField(max_length=60, blank=True, null=True)
    passport_image = models.FileField(upload_to="passports/%Y/%m/", blank=True, null=True)

    # VISA
    visa_type = models.CharField(max_length=100, blank=True, null=True)
    visa_expiry = models.DateField(blank=True, null=True)

    # TAGS
    tags = models.ManyToManyField(Tag, blank=True)

    # CONSENT
    consent_given = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(blank=True, null=True)

    # INTERNAL FIELDS
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students_created",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)

    # COURSE
    course = models.CharField(max_length=100, blank=True, null=True)

    # APPLICATION STATUS
    application_status = models.CharField(
        max_length=20,
        choices=APPLICATION_STATUS_CHOICES,
        default="pending",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.country or '—'})"


# ----------------------------------------------------
# STUDENT DOCUMENTS
# ----------------------------------------------------
class StudentDocument(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=128, blank=True)
    file = models.FileField(upload_to="student_documents/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title or 'Document'} — {self.student}"


# ----------------------------------------------------
# LEADS
# ----------------------------------------------------
class Lead(models.Model):
    SOURCE_CHOICES = (
        ("facebook", "Facebook"),
        ("manual", "Manual"),
        ("other", "Other"),
    )
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default="other")
    payload = models.JSONField()
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    student = models.ForeignKey(
        Student, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="leads",
    )

    # 🔽 NEW FIELDS FOR FACEBOOK ANALYTICS
    campaign_name = models.CharField(max_length=255, blank=True)
    adset_name = models.CharField(max_length=255, blank=True)
    ad_name = models.CharField(max_length=255, blank=True)
    fb_lead_id = models.CharField(max_length=100, blank=True)

    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assigned_leads",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source", "processed"]),
        ]


    def __str__(self):
        return f"Lead {self.id} ({self.source})"


# ----------------------------------------------------
# ACTIVITY LOG
# ----------------------------------------------------
class ActivityLog(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    student = models.ForeignKey(
        Student,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="activities",
    )

    action = models.CharField(max_length=150)
    data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.user or 'system'} on {self.created_at:%Y-%m-%d %H:%M}"


# ----------------------------------------------------
# SITE SETTINGS
# ----------------------------------------------------
class SiteConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)

    def __str__(self):
        return self.key


# ----------------------------------------------------
# EMAIL LOGGING
# ----------------------------------------------------
class EmailLog(models.Model):
    STATUS_CHOICES = (
        ("sent", "Sent"),
        ("failed", "Failed"),
    )

    student = models.ForeignKey(
        Student,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="email_logs",
    )
    lead = models.ForeignKey(
        Lead,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="email_logs",
    )

    to_email = models.EmailField()
    from_email = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="sent")
    error_message = models.TextField(blank=True)

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Email to {self.to_email} ({self.status})"


