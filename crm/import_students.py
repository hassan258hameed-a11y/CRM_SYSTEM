# crm/import_students.py

import os
from django.conf import settings
import pandas as pd
from django.db import transaction
from crm.models import Student, Country

# ---- Correct Excel file path ----
file_path = os.path.join(settings.BASE_DIR, "data", "students_with_course.xlsx")
print("Looking for file at:", file_path)

try:
    df = pd.read_excel(file_path)
    print("✅ Excel loaded! Rows:", len(df))
except Exception as e:
    print("❌ Error loading Excel:", e)
    df = pd.DataFrame()

# ---- Column Mapping for the new file ----
COLUMN_MAPPING = {
    'name': ['name', 'Name'],
    'phone': ['phone', 'Phone'],
    'email': ['email', 'Email'],
    'course': ['course', 'Course'],
    'enrollment_date': ['enrollment_date', 'Enrollment_Date'],
}

def get_value(row, options):
    """Return first found non-empty column."""
    for col in options:
        if col in row and pd.notna(row[col]):
            return row[col]
    return None

@transaction.atomic
def import_students_from_excel():

    if df.empty:
        print("❌ No data found in Excel. Import cancelled.")
        return

    for index, row in df.iterrows():

        name = get_value(row, COLUMN_MAPPING['name'])
        if not name:
            print(f"Skipping row {index}: Missing name")
            continue

        # If name has spaces → split to first/last name
        name_parts = str(name).strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        phone = get_value(row, COLUMN_MAPPING['phone'])
        email = get_value(row, COLUMN_MAPPING['email'])
        course = get_value(row, COLUMN_MAPPING['course'])
        enrollment_date = get_value(row, COLUMN_MAPPING['enrollment_date'])

        # Country is not in file now → optional
        country = None

        student = Student(
            first_name=first_name,
            last_name=last_name,
            phone=str(phone or "").strip(),
            email=str(email or "").strip(),
            course=str(course or "").strip() if hasattr(Student, "course") else "",
            enrollment_date=enrollment_date if hasattr(Student, "enrollment_date") else None,
            country=country,
        )

        student.save()
        print(f"Imported → {student.first_name} ({student.email})")

    print("🎉 Import Complete!")
