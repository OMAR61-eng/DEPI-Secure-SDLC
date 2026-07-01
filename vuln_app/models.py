"""
models.py — DEPI E-Learning Portal
===================================
Database schema for the University E-Learning platform.
Extended to cover additional OWASP Top 10 attack surfaces.
Vulnerabilities by design:
  • CWE-89   SQL Injection (raw queries in views)
  • CWE-79   XSS (stored & reflected)
  • CWE-284  IDOR (object IDs exposed, no ownership check)
  • CWE-287  Broken Authentication (plain-text passwords, no lockout)
  • CWE-200  Sensitive Data Exposure (PII fields, verbose errors)
  • CWE-522  Insufficiently Protected Credentials (plain-text storage)
  • CWE-916  Weak password hashing (none at all)
"""
from django.db import models

# ─── Users / Authentication ───────────────────────────────────────────────────
class Student(models.Model):
    """Portal user — intentionally stores plain-text password."""
    ROLE_CHOICES = [('student', 'Student'), ('instructor', 'Instructor'), ('admin', 'Admin')]

    student_id   = models.CharField(max_length=20, unique=True)   # e.g. DEPI-2024-0042
    full_name    = models.CharField(max_length=200)
    username     = models.CharField(max_length=100, unique=True)
    password     = models.CharField(max_length=255)               #  plain-text
    email        = models.EmailField()
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    department   = models.CharField(max_length=100, default='Computer Science')
    gpa          = models.DecimalField(max_digits=3, decimal_places=2, default=3.00)
    national_id  = models.CharField(max_length=20, blank=True)    #  sensitive PII
    phone        = models.CharField(max_length=20, blank=True)
    is_active    = models.BooleanField(default=True)
    login_attempts = models.IntegerField(default=0)               #  never locked out
    last_login   = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    class Meta:
        db_table = 'students'

# ─── Courses ──────────────────────────────────────────────────────────────────
class Course(models.Model):
    code        = models.CharField(max_length=20, unique=True)   # e.g. CS-401
    title       = models.CharField(max_length=200)
    description = models.TextField()
    instructor  = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, related_name='taught_courses')
    credits     = models.IntegerField(default=3)
    semester    = models.CharField(max_length=30, default='Fall 2024')
    is_active   = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} — {self.title}"

    class Meta:
        db_table = 'courses'

# ─── Enrollments ─────────────────────────────────────────────────────────────
class Enrollment(models.Model):
    """IDOR surface: /grades/<id>/ leaks any student's grade."""
    student   = models.ForeignKey(Student, on_delete=models.CASCADE)
    course    = models.ForeignKey(Course, on_delete=models.CASCADE)
    grade     = models.CharField(max_length=5, blank=True)        # A, B+, etc.
    score     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    feedback  = models.TextField(blank=True)                      # Stored XSS vector

    def __str__(self):
        return f"{self.student.username} → {self.course.code}"

    class Meta:
        db_table = 'enrollments'

# ─── Announcements (Stored XSS surface) ──────────────────────────────────────
class Announcement(models.Model):
    """Posted by instructors — content rendered raw → stored XSS."""
    title     = models.CharField(max_length=200)
    body      = models.TextField()                                #  rendered |safe
    author    = models.ForeignKey(Student, on_delete=models.CASCADE)
    course    = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    posted_at = models.DateTimeField(auto_now_add=True)
    is_pinned = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'announcements'

# ─── Support Tickets (IDOR + Stored XSS) ─────────────────────────────────────
class SupportTicket(models.Model):
    STATUS = [('open', 'Open'), ('in_progress', 'In Progress'), ('closed', 'Closed')]
    student     = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject     = models.CharField(max_length=200)
    description = models.TextField()                              #  rendered |safe
    status      = models.CharField(max_length=20, choices=STATUS, default='open')
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ticket #{self.id}: {self.subject}"

    class Meta:
        db_table = 'support_tickets'

# ─── LoginAudit (for brute-force demo) ───────────────────────────────────────
class LoginAudit(models.Model):
    """Logs every login attempt — no lockout enforced."""
    username   = models.CharField(max_length=100)
    src_ip     = models.GenericIPAddressField(null=True)
    success    = models.BooleanField(default=False)
    user_agent = models.TextField(blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'login_audit'