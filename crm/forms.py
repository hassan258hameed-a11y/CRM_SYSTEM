from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.auth import get_user_model

from .models import Student, StudentDocument, Country, Tag, Lead

User = get_user_model()


# ------------------------
# Single Email Form (per student)
# ------------------------
class EmailSendForm(forms.Form):
    subject = forms.CharField(
        label="Subject",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    body = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={"rows": 5, "class": "form-control"})
    )
    include_documents = forms.BooleanField(
        required=False,
        label="Attach all student documents",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"})
    )


# ------------------------
# Bulk Email Broadcast Form
# ------------------------
class EmailBroadcastForm(forms.Form):
    AUDIENCE_CHOICES = (
        ("all", "All students"),
        ("course", "By course"),
        ("country", "By country"),
        ("status", "By application status"),
    )

    audience = forms.ChoiceField(
        choices=AUDIENCE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    subject = forms.CharField(
        label="Subject",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    body = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={"rows": 5, "class": "form-control"})
    )

    # Optional filters
    course = forms.CharField(
        required=False,
        label="Course (for 'By course')",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    country = forms.ModelChoiceField(
        queryset=Country.objects.all(),
        required=False,
        label="Country (for 'By country')",
        widget=forms.Select(attrs={"class": "form-select"})
    )

    STATUS_FILTER_CHOICES = [("", "All statuses")] + list(Student.APPLICATION_STATUS_CHOICES)
    status = forms.ChoiceField(
        required=False,
        label="Application status (for 'By application status')",
        choices=STATUS_FILTER_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"})
    )



# ------------------------
# Student Form
# ------------------------
class StudentForm(forms.ModelForm):
    passport_image = forms.FileField(required=False)
    visa_expiry = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    enrollment_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'gender', 'country', 'phone', 'email',
            'passport_number', 'passport_image', 'visa_type', 'visa_expiry',
            'course', 'application_status', 'enrollment_date',
            'tags', 'consent_given', 'notes', 'archived'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'tags': forms.SelectMultiple(attrs={'size': 6, 'class': 'form-select'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'country': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'passport_number': forms.TextInput(attrs={'class': 'form-control'}),
            'visa_type': forms.TextInput(attrs={'class': 'form-control'}),
            'consent_given': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'archived': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'course': forms.TextInput(attrs={'class': 'form-control'}),
            'application_status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(
            Submit('submit', 'Save Student', css_class='btn-primary')
        )


# ------------------------
# WhatsApp Broadcast Form (NEW)
# ------------------------
class WhatsAppBroadcastForm(forms.Form):
    AUDIENCE_CHOICES = (
        ("all", "All students"),
        ("course", "Specific course"),
        ("batch", "Specific batch"),
        ("parents", "Parents"),
    )

    audience = forms.ChoiceField(
        choices=AUDIENCE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    course = forms.CharField(
        required=False,
        label="Course (for 'Specific course')",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    enrollment_year = forms.IntegerField(
        required=False,
        label="Enrollment year (for 'Specific batch')",
        widget=forms.NumberInput(attrs={"class": "form-control"})
    )

    body = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control"})
    )


# ------------------------
# Document Form
# ------------------------
class DocumentForm(forms.ModelForm):
    class Meta:
        model = StudentDocument
        fields = ['title', 'file', 'note']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(
            Submit('submit', 'Upload Document', css_class='btn-success')
        )


# ------------------------
# Student Filter Form
# ------------------------
class StudentFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={
            'placeholder': 'Name, email, or phone',
            'class': 'form-control'
        })
    )
    country = forms.ModelChoiceField(
        queryset=Country.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    tag = forms.ModelChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    archived = forms.ChoiceField(
        choices=(('', 'All'), ('0', 'Active'), ('1', 'Archived')),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# ------------------------
# Lead Form
# ------------------------
class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['source', 'phone', 'email', 'student', 'processed', 'assigned_to']
        widgets = {
            'source': forms.Select(attrs={'class': 'form-select'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'student': forms.Select(attrs={'class': 'form-select'}),
            'processed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(
            Submit('submit', 'Save Lead', css_class='btn-primary')
        )


# ------------------------
# User Edit Form (NEW)
# ------------------------
class UserEditForm(forms.ModelForm):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
    )

    # not in User model, but on the form
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        model = User
        # these are REAL fields on the User model
        fields = ['first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full rounded-2xl border-2 border-purple-400 px-4 py-2 '
                         'focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full rounded-2xl border-2 border-purple-400 px-4 py-2 '
                         'focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': 'Last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full rounded-2xl border-2 border-purple-400 px-4 py-2 '
                         'focus:ring-2 focus:ring-purple-500 focus:border-purple-500',
                'placeholder': 'user@example.com'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-purple-600 rounded focus:ring-purple-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # set initial role based on flags
        if self.instance and self.instance.pk:
            if self.instance.is_superuser:
                self.fields['role'].initial = 'admin'
            elif self.instance.is_staff:
                self.fields['role'].initial = 'manager'
            else:
                self.fields['role'].initial = 'staff'

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')

        if role == 'admin':
            user.is_superuser = True
            user.is_staff = True
        elif role == 'manager':
            user.is_superuser = False
            user.is_staff = True
        else:  # staff
            user.is_superuser = False
            user.is_staff = False

        if commit:
            user.save()
        return user
