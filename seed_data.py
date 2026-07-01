"""
seed_data.py — Populate the database with realistic academic data.
Run with: python seed_data.py  (from the project root)
"""
import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from vuln_app.models import Student, Course, Enrollment, Announcement, SupportTicket

print('[*] Seeding database with academic records...')

SupportTicket.objects.all().delete()
Announcement.objects.all().delete()
Enrollment.objects.all().delete()
Course.objects.all().delete()
Student.objects.all().delete()

# 1. إضافة الطلاب والدكاترة (بيانات ضخمة)
students = [
    # 👨‍🎓 Students
    Student(student_id='DEPI-2026-0001', full_name='Ahmed Hassan', username='ahmed', password='ahmed123', email='ahmed@depi.gov.eg', role='student', department='Computer Science', gpa=Decimal('3.65'), national_id='30102010123456', phone='01000000001'),
    Student(student_id='DEPI-2026-0002', full_name='Mona Adel', username='mona', password='mona123', email='mona@depi.gov.eg', role='student', department='Information Systems', gpa=Decimal('3.82'), national_id='30105020123456', phone='01000000002'),
    Student(student_id='DEPI-2026-0003', full_name='Karim Soliman', username='karim', password='karim123', email='karim@depi.gov.eg', role='student', department='Cybersecurity', gpa=Decimal('3.21'), national_id='30108030123456', phone='01000000003'),
    Student(student_id='DEPI-2026-0004', full_name='Nour El-Din', username='nour', password='nour123', email='nour@depi.gov.eg', role='student', department='Computer Science', gpa=Decimal('3.91'), national_id='30111040123456', phone='01000000004'),
    Student(student_id='DEPI-2026-0009', full_name='Yassin Mahmoud', username='yassin', password='password123', email='yassin@depi.gov.eg', role='student', department='Cybersecurity', gpa=Decimal('2.95'), national_id='30201010123456', phone='01111111111'),
    Student(student_id='DEPI-2026-0010', full_name='Salma Yasser', username='salma', password='password123', email='salma@depi.gov.eg', role='student', department='Software Engineering', gpa=Decimal('3.40'), national_id='30205050123456', phone='01222222222'),
    
    # 👨‍🏫 Instructors
    Student(student_id='DEPI-2026-0005', full_name='Dr. Sara Ibrahim', username='sara', password='sara123', email='sara@depi.gov.eg', role='instructor', department='Computer Science', gpa=Decimal('4.00'), national_id='29803050123456', phone='01000000005'),
    Student(student_id='DEPI-2026-0006', full_name='Dr. Youssef Farid', username='youssef', password='youssef123', email='youssef@depi.gov.eg', role='instructor', department='Software Engineering', gpa=Decimal('3.95'), national_id='29612060123456', phone='01000000006'),
    Student(student_id='DEPI-2026-0007', full_name='Dr. Hoda Magdy', username='hoda', password='hoda123', email='hoda@depi.gov.eg', role='instructor', department='Information Systems', gpa=Decimal('3.88'), national_id='29507070123456', phone='01000000007'),
    Student(student_id='DEPI-2026-0011', full_name='Dr. Tarek Ziad', username='tarek', password='tarek_sec', email='tarek@depi.gov.eg', role='instructor', department='Cybersecurity', gpa=Decimal('4.00'), national_id='29001010123456', phone='01555555555'),
    Student(student_id='DEPI-2026-0013', full_name='Dr. Amr Adel', username='amr', password='amr123', email='amr@depi.gov.eg', role='instructor', department='Cybersecurity', gpa=Decimal('3.90'), national_id='29102010123456', phone='01666666666'),
    
    # 👑 Admins
    Student(student_id='DEPI-2026-0008', full_name='Admin User', username='admin', password='admin123', email='admin@depi.gov.eg', role='admin', department='IT', gpa=Decimal('4.00'), national_id='30001080123456', phone='01000000008'),
    Student(student_id='DEPI-2026-0012', full_name='Super Admin', username='root', password='SuperSecretPassword!', email='root@depi.gov.eg', role='admin', department='IT', gpa=Decimal('4.00'), national_id='30001080123999', phone='01000000099'),
]
Student.objects.bulk_create(students)
created_students = list(Student.objects.order_by('id'))
amr_instructor = next((s for s in created_students if s.username == 'amr'), None)
instructors = [s for s in created_students if s.role == 'instructor']
students_only = [s for s in created_students if s.role == 'student']

# 2. إضافة الكورسات
courses = [
    Course(code='CS-401', title='Advanced Database Systems', description='Modern database concepts, indexing, transactions, and optimization.', instructor=instructors[0], credits=3, semester='Fall 2026', is_active=True),
    Course(code='CS-402', title='Software Security', description='Secure software engineering and common application vulnerabilities.', instructor=instructors[1], credits=3, semester='Fall 2026', is_active=True),
    Course(code='IS-301', title='Business Intelligence', description='Data analytics and reporting for decision support.', instructor=instructors[2], credits=3, semester='Fall 2026', is_active=True),
    Course(code='CYB-501', title='SOC Operations & Log Analysis', description='Enterprise monitoring, Splunk SIEM, and Threat Hunting.', instructor=amr_instructor, credits=4, semester='Fall 2026', is_active=True),
    Course(code='CYB-502', title='Digital Forensics & Incident Response', description='Investigating breaches and containing cyber threats.', instructor=instructors[3], credits=4, semester='Fall 2026', is_active=True),
    Course(code='SE-410', title='Cloud Computing', description='Distributed systems and cloud deployment strategies.', instructor=instructors[1], credits=3, semester='Fall 2026', is_active=True),
]
Course.objects.bulk_create(courses)
created_courses = list(Course.objects.order_by('id'))

# 3. إضافة التسجيلات والدرجات
enrollments = [
    Enrollment(student=students_only[0], course=created_courses[0], grade='A', score=Decimal('92.50'), feedback='Excellent work.'),
    Enrollment(student=students_only[1], course=created_courses[1], grade='B+', score=Decimal('84.00'), feedback='Solid understanding of security.'),
    Enrollment(student=students_only[2], course=created_courses[3], grade='A+', score=Decimal('98.00'), feedback='Exceptional SOC log analysis skills!'),
    Enrollment(student=students_only[3], course=created_courses[4], grade='A', score=Decimal('90.00'), feedback='Great incident report.'),
    Enrollment(student=students_only[4], course=created_courses[3], grade='C', score=Decimal('65.00'), feedback='Needs to focus more on SIEM rules.'),
    Enrollment(student=students_only[5], course=created_courses[0], grade='B', score=Decimal('82.00'), feedback='Good database design.'),
]
Enrollment.objects.bulk_create(enrollments)

# 4. إضافة الإعلانات
announcements = [
    Announcement(title='Welcome Back Students', body='The portal is now populated with live academic records. Check your schedules.', author=created_students[6], course=created_courses[0], is_pinned=True),
    Announcement(title='SOC Lab Maintenance', body='The Splunk servers will be down for maintenance this Friday.', author=created_students[9], course=created_courses[3], is_pinned=False),
    Announcement(title='Security Alert!', body='Please do not share your portal passwords. We noticed suspicious login attempts.', author=created_students[10], course=None, is_pinned=True),
]
Announcement.objects.bulk_create(announcements)

# 5. إضافة تذاكر الدعم الفني
support_tickets = [
    SupportTicket(student=students_only[0], subject='Access to course materials', description='I need help accessing the notes.'),
    SupportTicket(student=students_only[2], subject='Splunk Lab Credentials', description='I lost my VPN access to the SOC lab.'),
    SupportTicket(student=students_only[4], subject='Portal login issue', description='I am unable to log in after resetting my password.'),
    SupportTicket(student=students_only[5], subject='Change Department', description='Can I transfer from SE to Cybersecurity?'),
]
SupportTicket.objects.bulk_create(support_tickets)

print(f'  [+] Created {Student.objects.count()} students & staff')
print(f'  [+] Created {Course.objects.count()} courses')
print(f'  [+] Created {Enrollment.objects.count()} enrollments')
print(f'  [+] Created {Announcement.objects.count()} announcements')
print(f'  [+] Created {SupportTicket.objects.count()} support tickets')
print('\n[✓] Database seeded successfully! Ready for Pentesting.')