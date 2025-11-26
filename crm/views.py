from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
User = get_user_model()

from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from django.core.mail import EmailMessage
from django.conf import settings
import json

from .models import (
    Student,
    Lead,
    Country,
    Tag,
    StudentDocument,
    ActivityLog,
    EmailLog,
)

from .forms import (
    StudentForm,
    DocumentForm,
    StudentFilterForm,
    LeadForm,
    UserEditForm,
    EmailSendForm,
    EmailBroadcastForm,
)




# -------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------

DOC_FIELDS = [
    ("passport", "Passport (Optional)"),
    ("transcript", "Transcript (Optional)"),
    ("degree_certificate", "Degree Certificate (Optional)"),
    ("ielts_toefl", "IELTS/TOEFL Score (Optional)"),
    ("sop", "Statement of Purpose (Optional)"),
    ("lor", "Letter of Recommendation (Optional)"),
    ("financial_docs", "Financial Documents (Optional)"),
    ("passport_photo", "Passport Photo (Optional)"),
]


# -------------------------------------------------------
# SEND EMAIL TO SINGLE STUDENT
# -------------------------------------------------------
@login_required
@require_http_methods(["GET", "POST"])
def student_send_email(request, pk):
    student = get_object_or_404(Student, pk=pk)

    if not student.email:
        messages.error(request, "This student does not have an email address.")
        return redirect("student_detail", pk=pk)

    if request.method == "POST":
        form = EmailSendForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            body = form.cleaned_data["body"]
            include_docs = form.cleaned_data["include_documents"]

            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[student.email],
            )

            if include_docs:
                for doc in student.documents.all():
                    if doc.file:
                        try:
                            email.attach_file(doc.file.path)
                        except Exception:
                            # ignore missing files
                            pass

            status = "sent"
            error = ""

            try:
                email.send()
                messages.success(request, "Email sent successfully.")
            except Exception as e:
                status = "failed"
                error = str(e)
                messages.error(request, "Failed to send email. Please check email settings.")

            EmailLog.objects.create(
                student=student,
                to_email=student.email,
                from_email=settings.DEFAULT_FROM_EMAIL,
                subject=subject,
                body=body,
                status=status,
                error_message=error,
            )

            return redirect("student_detail", pk=pk)
    else:
        initial_body = f"Hi {student.first_name},\n\n"
        form = EmailSendForm(
            initial={
                "subject": "Regarding your application",
                "body": initial_body,
            }
        )

    return render(
        request,
        "crm/student_send_email.html",
        {"student": student, "form": form},
    )
# -------------------------------------------------------
# EMAIL INTEGRATION DASHBOARD
# -------------------------------------------------------
@login_required
def email_integration(request):
    broadcast_form = EmailBroadcastForm()
    recent_emails = EmailLog.objects.select_related("student", "lead")[:30]

    return render(
        request,
        "crm/email_integration.html",
        {
            "broadcast_form": broadcast_form,
            "recent_emails": recent_emails,
        },
    )


# -------------------------------------------------------
# EMAIL BROADCAST HANDLER
# -------------------------------------------------------
@login_required
@require_POST
def email_broadcast(request):
    form = EmailBroadcastForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Please fix the errors in the form.")
        return redirect("email_integration")

    audience = form.cleaned_data["audience"]
    subject = form.cleaned_data["subject"]
    body = form.cleaned_data["body"]
    course = form.cleaned_data["course"]
    country = form.cleaned_data["country"]
    status = form.cleaned_data["status"]

    qs = Student.objects.filter(archived=False).exclude(email="")

    if audience == "course" and course:
        qs = qs.filter(course__icontains=course)
    elif audience == "country" and country:
        qs = qs.filter(country=country)
    elif audience == "status" and status:
        qs = qs.filter(application_status=status)

    total = qs.count()
    if total == 0:
        messages.warning(request, "No students matched your filters.")
        return redirect("email_integration")

    sent_count = 0

    for student in qs:
        personalized_body = body.replace("{{ first_name }}", student.first_name or "")

        email = EmailMessage(
            subject=subject,
            body=personalized_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email],
        )

        status_flag = "sent"
        error_msg = ""

        try:
            email.send()
            sent_count += 1
        except Exception as e:
            status_flag = "failed"
            error_msg = str(e)

        EmailLog.objects.create(
            student=student,
            to_email=student.email,
            from_email=settings.DEFAULT_FROM_EMAIL,
            subject=subject,
            body=personalized_body,
            status=status_flag,
            error_message=error_msg,
        )

    messages.success(
        request,
        f"Broadcast finished. Sent {sent_count} emails out of {total} students.",
    )
    return redirect("email_integration")

# -------------------------------------------------------
# STUDENTS LIST
# -------------------------------------------------------

def students_list(request):
    qs = Student.objects.select_related("country").prefetch_related("tags")
    form = StudentFilterForm(request.GET or None)

    if form.is_valid():
        q = form.cleaned_data.get("q")
        country = form.cleaned_data.get("country")
        tag = form.cleaned_data.get("tag")
        archived = form.cleaned_data.get("archived")

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(passport_number__icontains=q)
            )

        if country:
            qs = qs.filter(country=country)
        if tag:
            qs = qs.filter(tags=tag)

        if archived == "1":
            qs = qs.filter(archived=True)
        elif archived == "0":
            qs = qs.filter(archived=False)
        else:
            qs = qs.filter(archived=False)

    # ordering & pagination
    qs = qs.order_by("-created_at")
    page = request.GET.get("page", 1)
    paginator = Paginator(qs, 12)

    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)

    return render(
        request,
        "crm/students_list.html",
        {"students": students, "filter_form": form},
    )


# -------------------------------------------------------
# MANAGE USERS
# -------------------------------------------------------

@require_http_methods(["GET"])
def manage_users(request):
    qs = User.objects.all().order_by("id")

    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    status = request.GET.get("status", "")

    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )

    if role == "admin":
        qs = qs.filter(is_superuser=True)
    elif role == "manager":
        qs = qs.filter(is_staff=True, is_superuser=False)
    elif role == "staff":
        qs = qs.filter(is_staff=False, is_superuser=False)

    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)

    context = {
        "users": qs,
        "search_q": q,
        "filter_role": role,
        "filter_status": status,
        "total_users": User.objects.count(),
        "active_count": User.objects.filter(is_active=True).count(),
        "inactive_count": User.objects.filter(is_active=False).count(),
        "admins_count": User.objects.filter(is_superuser=True).count(),
        "managers_count": User.objects.filter(is_staff=True, is_superuser=False).count(),
        "staff_count": User.objects.filter(is_staff=False, is_superuser=False).count(),
    }

    return render(request, "crm/manage_users.html", context)


@require_http_methods(["GET"])
def user_detail(request, pk):
    user_obj = get_object_or_404(User, pk=pk)
    role_label = (
        "Admin" if user_obj.is_superuser else "Manager" if user_obj.is_staff else "Staff"
    )
    return render(
        request,
        "crm/user_detail.html",
        {"user_obj": user_obj, "role_label": role_label},
    )


@login_required
def user_edit(request, pk):
    user_obj = get_object_or_404(User, pk=pk)

    if user_obj.is_superuser and request.user != user_obj:
        messages.error(request, "You cannot edit another admin.")
        return redirect("manage_users")

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            user = form.save(commit=False)
            status_value = request.POST.get("status", "active")
            user.is_active = status_value == "active"
            user.save()
            messages.success(request, "User updated successfully.")
            return redirect("manage_users")
    else:
        form = UserEditForm(instance=user_obj)

    return render(
        request,
        "crm/user_edit.html",
        {
            "form": form,
            "user_obj": user_obj,
            "perms": ["Students", "Applications", "Users", "Email", "AI", "Integration", "All"],
            "current_status": "active" if user_obj.is_active else "inactive",
        },
    )


@require_http_methods(["POST"])
def user_delete(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission.")
        return redirect("manage_users")

    user_obj = get_object_or_404(User, pk=pk)

    if user_obj.is_superuser or user_obj == request.user:
        messages.error(request, "Cannot delete this user.")
        return redirect("manage_users")

    user_obj.delete()
    messages.success(request, "User deleted.")
    return redirect("manage_users")


# -------------------------------------------------------
# APPLICATIONS LIST
# -------------------------------------------------------

def applications_list(request):
    base_qs = Student.objects.select_related("country").prefetch_related("documents")

    search_q = request.GET.get("q", "").strip()
    filter_status = request.GET.get("status", "").strip()
    filter_country = request.GET.get("country", "").strip()

    qs = base_qs

    if search_q:
        qs = qs.filter(
            Q(first_name__icontains=search_q)
            | Q(last_name__icontains=search_q)
            | Q(course__icontains=search_q)
        )

    if filter_status:
        qs = qs.filter(application_status=filter_status)

    if filter_country:
        qs = qs.filter(country_id=filter_country)

    context = {
        "applications": qs,
        "total_apps": base_qs.count(),
        "pending_count": base_qs.filter(application_status="pending").count(),
        "under_review_count": base_qs.filter(application_status="under_review").count(),
        "approved_count": base_qs.filter(application_status="approved").count(),
        "rejected_count": base_qs.filter(application_status="rejected").count(),
        "search_q": search_q,
        "filter_status": filter_status,
        "filter_country": filter_country,
        "status_choices": Student.APPLICATION_STATUS_CHOICES,
        "countries": Country.objects.all(),
    }

    return render(request, "crm/applications_list.html", context)


# -------------------------------------------------------
# AJAX UPDATE APPLICATION STATUS
# -------------------------------------------------------

@csrf_exempt
@require_POST
def application_update_status(request):
    app_id = request.POST.get("id")
    new_status = request.POST.get("status")

    allowed = [s[0] for s in Student.APPLICATION_STATUS_CHOICES]
    if new_status not in allowed:
        return JsonResponse({"success": False, "error": "Invalid status"}, status=400)

    try:
        student = Student.objects.get(pk=app_id)
    except Student.DoesNotExist:
        return JsonResponse({"success": False, "error": "Not found"}, status=404)

    student.application_status = new_status
    student.save(update_fields=["application_status"])

    return JsonResponse({"success": True, "status": new_status})




# -------------------------------------------------------
# STUDENT CRUD
# -------------------------------------------------------

@require_http_methods(["GET", "POST"])
def student_create(request):
    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            student = form.save(commit=False)

            if request.user.is_authenticated:
                student.created_by = request.user

            if student.consent_given and not student.consent_timestamp:
                student.consent_timestamp = timezone.now()

            student.save()
            form.save_m2m()

            for field_name, label in DOC_FIELDS:
                uploaded = request.FILES.get(field_name)
                if uploaded:
                    StudentDocument.objects.create(student=student, title=label, file=uploaded)

            messages.success(request, "Student added successfully.")
            return redirect("student_detail", pk=student.pk)
    else:
        form = StudentForm()

    return render(request, "crm/student_create.html", {"form": form, "student": None, "docs": DOC_FIELDS})


@require_http_methods(["GET", "POST"])
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)

    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES, instance=student)

        if form.is_valid():
            student = form.save(commit=False)

            if student.consent_given and not student.consent_timestamp:
                student.consent_timestamp = timezone.now()

            student.save()
            form.save_m2m()

            for field_name, label in DOC_FIELDS:
                uploaded = request.FILES.get(field_name)
                if uploaded:
                    StudentDocument.objects.create(student=student, title=label, file=uploaded)

            messages.success(request, "Student updated successfully.")
            return redirect("students_list")
    else:
        form = StudentForm(instance=student)

    return render(request, "crm/student_create.html", {"form": form, "student": student, "docs": DOC_FIELDS})


@require_http_methods(["GET", "POST"])
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    doc_form = DocumentForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and doc_form.is_valid():
        doc = doc_form.save(commit=False)
        doc.student = student
        doc.save()

        ActivityLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            student=student,
            action="uploaded_document",
            data={"document_id": doc.id},
        )

        messages.success(request, "Document uploaded.")
        return redirect("student_detail", pk=pk)

    activities = student.activities.all()[:20]

    return render(
        request,
        "crm/student_detail.html",
        {"student": student, "doc_form": doc_form, "activities": activities},
    )


# -------------------------------------------------------
# LEADS LIST
# -------------------------------------------------------

def leads_list(request):
    qs = Lead.objects.select_related("student").order_by("-created_at")
    paginator = Paginator(qs, 25)
    page = request.GET.get("page")

    try:
        leads = paginator.page(page)
    except:
        leads = paginator.page(1)

    return render(request, "crm/leads_list.html", {"leads": leads})


# -------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------

def dashboard(request):
    context = {
        "total_students": Student.objects.count(),
        "new_this_month": Student.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count(),
        "total_applications": Student.objects.count(),
        "growth_rate": "+12%",
    }
    return render(request, "crm/dashboard.html", context)


@require_GET
def dashboard_stats(request):
    country_qs = (
        Student.objects.values("country__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    lead_qs = Lead.objects.values("source").annotate(count=Count("id"))

    data = {
        "countries": [c["country__name"] or "Unknown" for c in country_qs],
        "country_counts": [c["count"] for c in country_qs],
        "lead_labels": [l["source"] for l in lead_qs],
        "lead_counts": [l["count"] for l in lead_qs],
        "recent_students": Student.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count(),
        "total_students": Student.objects.count(),
        "total_leads": Lead.objects.count(),
    }

    return JsonResponse(data)

    # views.py
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect
from .forms import StudentForm   # or a special PublicStudentForm
from .models import Student, Lead   # adjust if your names differ


@require_http_methods(["GET", "POST"])
def public_apply(request):
    """
    Public 'Apply Now' form for students coming from Facebook / website.
    No login required.
    """
    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES)  # or PublicStudentForm
        if form.is_valid():
            student = form.save()

            # optional: track that this came from Facebook / website
            Lead.objects.create(
                student=student,
                source="facebook-website",     # adjust field names to your model
                notes="Submitted via public apply form",
            )

            return render(request, "public_thank_you.html", {"student": student})
    else:
        form = StudentForm()

    return render(request, "public_apply.html", {"form": form})



# -------------------------------------------------------
# LEAD WEBHOOK
# -------------------------------------------------------

@csrf_exempt
@require_http_methods(["POST"])
def webhook_lead(request):
    """
    Generic lead webhook.

    Expected JSON payload (example from Zapier/Make/Facebook):
    {
        "source": "facebook",
        "full_name": "Ali Khan",
        "first_name": "Ali",             # optional
        "last_name": "Khan",             # optional
        "email": "ali@example.com",
        "phone": "+923001234567",
        "course": "Computer Science",
        "country": "Pakistan",
        "intake": "September 2025",
        "facebook": {
            "lead_id": "1234567890",
            "campaign_name": "Sep Intake 2025",
            "adset_name": "Pakistan - CS",
            "ad_name": "Main Lead Form Ad"
        }
    }
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON"},
            status=400,
        )

    # --- 1) Extract core fields from payload ---
    source = data.get("source", "facebook")

    phone = data.get("phone") or data.get("phone_number")
    email = data.get("email")

    full_name = data.get("full_name", "") or ""
    first_name = data.get("first_name") or ""
    last_name = data.get("last_name") or ""

    # If only full_name provided, split it
    if not first_name and full_name:
        parts = full_name.strip().split(" ", 1)
        first_name = parts[0]
        if len(parts) > 1:
            last_name = parts[1]

    course = data.get("course") or data.get("interested_course")
    country_name = data.get("country")  # e.g. "Pakistan"

    # --- 2) Try to find existing student by phone/email ---
    student = None

    if phone:
        student = Student.objects.filter(phone=phone).first()

    if not student and email:
        student = Student.objects.filter(email=email).first()

    # --- 3) If no student exists, create one from this lead ---
    new_student = False
    if not student:
        student = Student(
            first_name=first_name or "Facebook",
            last_name=last_name or "Lead",
            phone=phone or "",
            email=email or "",
            course=course or "",
        )

        # set country if given
        if country_name:
            country_obj, _ = Country.objects.get_or_create(name=country_name)
            student.country = country_obj

        student.save()
        new_student = True

        # Tag as "Facebook Lead"
        fb_tag, _ = Tag.objects.get_or_create(name="Facebook Lead")
        student.tags.add(fb_tag)

    # --- 4) Choose counselor to assign this lead to (optional but useful) ---
    counselor = (
        User.objects.filter(is_active=True, is_staff=True)
        .order_by("id")
        .first()
    )

    # --- 5) Create Lead record ---
    # If you added extra fields in Lead (campaign_name, adset_name, ad_name, fb_lead_id),
    # this will populate them from the nested "facebook" object.
    facebook_data = data.get("facebook", {}) or {}

    lead = Lead.objects.create(
        source=source or "facebook",
        phone=phone,
        email=email,
        student=student,
        payload=data,   # store raw JSON for later analysis
        assigned_to=counselor,
        # 🔻 these four lines require the fields to exist on Lead model
        campaign_name=facebook_data.get("campaign_name", ""),
        adset_name=facebook_data.get("adset_name", ""),
        ad_name=facebook_data.get("ad_name", ""),
        fb_lead_id=facebook_data.get("lead_id", ""),
    )

    # --- 6) Activity Log (optional but nice) ---
    ActivityLog.objects.create(
        user=None,
        student=student,
        action="lead_created",
        data={
            "source": source,
            "lead_id": lead.id,
            "new_student_created": new_student,
        },
    )

    return JsonResponse(
        {
            "status": "ok",
            "lead_id": lead.id,
            "student_id": student.id,
            "new_student": new_student,
        }
    )
@login_required
def facebook_integration(request):
    """
    Dashboard for Facebook → CRM integration.
    Shows webhook URL and all Facebook leads.
    """
    # Full URL for your webhook that Zapier/Make/Facebook will call
    webhook_url = request.build_absolute_uri(reverse("webhook_lead"))

    # All leads with source="facebook"
    fb_leads_qs = (
        Lead.objects.filter(source="facebook")
        .select_related("student")
        .order_by("-created_at")
    )

    stats = {
        "total_fb_leads": fb_leads_qs.count(),
        "last_30_days": fb_leads_qs.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count(),
    }

    return render(
        request,
        "crm/facebook_integration.html",
        {
            "webhook_url": webhook_url,
            "fb_leads": fb_leads_qs,
            "stats": stats,
        },
    )


