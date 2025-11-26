from django.contrib import admin
from .models import Student, Lead, StudentDocument, ActivityLog, Country, Tag, SiteConfig

class StudentDocumentInline(admin.TabularInline):
    model = StudentDocument
    extra = 0
    readonly_fields = ('uploaded_at',)

class ActivityInline(admin.StackedInline):
    model = ActivityLog
    extra = 0
    readonly_fields = ('created_at', 'user', 'action', 'data')
    can_delete = False

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'country', 'phone', 'email', 'created_at', 'archived')
    list_filter = ('country', 'archived', 'visa_type',)
    search_fields = ('first_name','last_name','email','phone','passport_number')
    inlines = [StudentDocumentInline, ActivityInline]
    readonly_fields = ('created_at','updated_at','consent_timestamp')
    actions = ['mark_archived','export_selected']

    def mark_archived(self, request, queryset):
        updated = queryset.update(archived=True)
        self.message_user(request, f"{updated} student(s) marked archived.")
    mark_archived.short_description = "Mark selected students as archived"

    def export_selected(self, request, queryset):
        # simple CSV export action
        import csv
        from django.http import HttpResponse
        fieldnames = ['id','first_name','last_name','email','phone','country','passport_number','visa_type','visa_expiry']
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=students_export.csv'
        writer = csv.writer(response)
        writer.writerow(fieldnames)
        for s in queryset:
            writer.writerow([getattr(s,f) if not callable(getattr(s,f,'')) else '' for f in fieldnames])
        return response
    export_selected.short_description = "Export selected students to CSV"

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('id','source','phone','email','student','processed','created_at','assigned_to')
    list_filter = ('source','processed','created_at')
    search_fields = ('phone','email')
    readonly_fields = ('payload','created_at')

@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ('id','title','student','uploaded_at')
    search_fields = ('title','student__first_name','student__last_name')

@admin.register(ActivityLog)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('id','action','user','student','created_at')
    readonly_fields = ('data',)

admin.site.register(Country)
admin.site.register(Tag)
admin.site.register(SiteConfig)
