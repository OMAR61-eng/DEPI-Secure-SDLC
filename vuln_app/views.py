import json
import datetime
import os
import re
import subprocess
from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.hashers import make_password, check_password
from .models import Student, Course, Enrollment, Announcement, SupportTicket, LoginAudit

def _get_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '0.0.0.0')

def home(request):
    announcements = Announcement.objects.select_related('author', 'course').order_by('-is_pinned', '-posted_at')[:6]
    courses = Course.objects.filter(is_active=True).select_related('instructor').order_by('code')[:6]

    active_courses = Course.objects.filter(is_active=True).count()
    enrolled_students = Enrollment.objects.values('student').distinct().count()
    faculty_members = Student.objects.filter(role='instructor').count()

    graded_enrollments = Enrollment.objects.exclude(score=0).exclude(grade='')
    if graded_enrollments.exists():
        passed = sum(1 for enrollment in graded_enrollments if float(enrollment.score) >= 60)
        pass_rate = round((passed / graded_enrollments.count()) * 100)
    else:
        pass_rate = 0

    return render(request, 'vuln_app/home.html', {
        'announcements': announcements,
        'courses': courses,
        'stats': {
            'active_courses': active_courses,
            'enrolled_students': enrolled_students,
            'faculty_members': faculty_members,
            'pass_rate': pass_rate,
        },
    })



from django_ratelimit.decorators import ratelimit


@ratelimit(key='ip', rate='5/m', block=True)
def login_view(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        src_ip = _get_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')

        try:
            user = Student.objects.filter(username=username).first()
            authenticated = bool(user and check_password(password, user.password))
        except Exception:
            LoginAudit.objects.create(username=username, src_ip=src_ip, success=False, user_agent=ua)
            return render(request, 'vuln_app/login.html', {'error': 'A database error occurred.'})

        LoginAudit.objects.create(username=username, src_ip=src_ip, success=authenticated, user_agent=ua)

        if authenticated:
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            request.session['role'] = user.role
            request.session['full_name'] = user.full_name
            return redirect('dashboard')
        else:
            error = 'Invalid username or password.'

    return render(request, 'vuln_app/login.html', {'error': error})

def logout_view(request):
    request.session.flush()
    return redirect('login')

def dashboard(request):
    if 'username' not in request.session:
        return redirect('login')
    username = request.session['username']
    role     = request.session.get('role', 'student')
    student  = Student.objects.filter(username=username).first()
    student_name = student.full_name if student else request.session.get('full_name') or request.session.get('username') or 'Student'
    enrollments = Enrollment.objects.filter(student=student).select_related('course') if student else []
    announcements = Announcement.objects.order_by('-posted_at')[:5]
    return render(request, 'vuln_app/dashboard.html', {
        'student': student,
        'student_name': student_name,
        'role': role,
        'enrollments': enrollments,
        'announcements': announcements,
    })

def search(request):
    q = request.GET.get('q', '')
    results = []
    db_error = None
    if q:
        try:
            qs = Course.objects.filter(Q(title__icontains=q) | Q(code__icontains=q))
            results = list(qs.values('id', 'code', 'title', 'description'))
        except Exception as exc:
            db_error = 'Search error'

    context = {
        'q': q,
        'results': results,
        'db_error': db_error,
    }
    return render(request, 'vuln_app/search.html', context)

def course_detail(request):
    course_id = request.GET.get('id', None)
    course_obj = None
    enrolled_students = []
    instructors = []

    if course_id:
        try:
            cid = int(course_id)
            course_obj = get_object_or_404(Course, pk=cid)
            enrolled_students = list(Enrollment.objects.filter(course=course_obj).select_related('student').order_by('student__full_name'))
            instructors = [course_obj.instructor] if course_obj.instructor else []
            result = {
                'id': course_obj.id,
                'code': course_obj.code,
                'title': course_obj.title,
                'description': course_obj.description,
                'credits': course_obj.credits,
                'semester': course_obj.semester,
            }
            db_error = None
        except ValueError:
            result = None
            db_error = 'Invalid course id.'
        except Exception as exc:
            result = None
            db_error = 'Course fetch error.'
    else:
        result = None
        db_error = 'Course id not provided.'

    return render(request, 'vuln_app/course_detail.html', {
        'result': result,
        'db_error': db_error,
        'course_id': course_id,
        'course': course_obj,
        'enrolled_students': enrolled_students,
        'instructors': instructors,
    })

def grades(request, enrollment_id):
    if 'username' not in request.session:
        return redirect('login')
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    return render(request, 'vuln_app/grades.html', {'enrollment': enrollment})

def my_grades(request):
    if 'username' not in request.session:
        return redirect('login')
    student     = Student.objects.filter(username=request.session['username']).first()
    enrollments = Enrollment.objects.filter(student=student).select_related('course') if student else []
    return render(request, 'vuln_app/my_grades.html', {'enrollments': enrollments, 'student': student})

def announcements(request):
    if request.method == 'POST':
        if request.session.get('role') not in ('instructor', 'admin'):
            return HttpResponse('Forbidden', status=403)
        author = Student.objects.filter(username=request.session['username']).first()
        course_id = request.POST.get('course_id')
        raw_body = request.POST.get('body', '')
        Announcement.objects.create(
            title=request.POST.get('title', ''),
            body=raw_body,
            author=author,
            course_id=course_id if course_id else None,
            is_pinned=bool(request.POST.get('is_pinned')),
        )
        return redirect('announcements')
    all_ann  = Announcement.objects.select_related('author', 'course').order_by('-posted_at')
    courses  = Course.objects.all()
    return render(request, 'vuln_app/announcements.html', {'announcements': all_ann, 'courses': courses})

def tickets(request):
    if 'username' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        student = Student.objects.filter(username=request.session['username']).first()
        SupportTicket.objects.create(
            student=student,
            subject=request.POST.get('subject', ''),
            description=request.POST.get('description', ''),
        )
        return redirect('tickets')
    all_tickets = SupportTicket.objects.select_related('student').order_by('-created_at')
    return render(request, 'vuln_app/tickets.html', {'tickets': all_tickets})

def ticket_detail(request, ticket_id):
    if 'username' not in request.session:
        return redirect('login')
    ticket = get_object_or_404(SupportTicket, id=ticket_id)
    return render(request, 'vuln_app/ticket_detail.html', {'ticket': ticket})

from django.http import JsonResponse
from django.shortcuts import redirect, render

def profile_page(request):
    if 'username' not in request.session:
        return redirect('login')

    profile_id = request.GET.get('id')
    student = None
    if profile_id:
        try:
            pid = int(profile_id)
            student = get_object_or_404(Student, id=pid)
            # Authorization: only admin or owner may view
            if request.session.get('role') != 'admin' and student.username != request.session.get('username'):
                return HttpResponse('Forbidden', status=403)
        except ValueError:
            return HttpResponse('Invalid profile id', status=400)
    return render(request, 'vuln_app/profile.html', {'student': student})


def profile_api(request, student_id):
    # [FIX: AUTHENTICATION CHECK]
    # Ensure the user making the API request is logged in
    if 'username' not in request.session:
        return JsonResponse({'error': 'Authentication required. Please log in.'}, status=401)
        
    logged_in_username = request.session.get('username')
    logged_in_role     = request.session.get('role', '').lower()

    try:
        # Fetch the target profile record safely using Django ORM
        s = Student.objects.get(student_id=student_id)
        # [FIX: BROKEN OBJECT LEVEL AUTHORIZATION (BOLA) PREVENTION]
        # Access control rule: A user can access the profile ONLY if:
        # 1. They are an 'admin'
        # 2. The target profile matches their own logged-in username
        if logged_in_role != 'admin' and s.username != logged_in_username:
            return JsonResponse({'error': 'Access Denied: Unauthorized to view this profile.'}, status=403)
            
        # Data is safely returned only after verifying permission checks
        data = {
            'id': s.id, 
            'student_id': s.student_id, 
            'full_name': s.full_name,
            'email': s.email, 
            'department': s.department, 
            'gpa': str(s.gpa),
            'national_id': s.national_id,
            'phone': s.phone,
            'role': s.role,
        }
        return JsonResponse(data)
        
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)


def debug_info(request):
    # Restrict debug info to admin users only
    if request.session.get('role') != 'admin':
        return JsonResponse({'error': 'Forbidden'}, status=403)

    info = {
        'server': 'Django/4.2 Python/3.11 Windows-Server',
        'debug': bool(settings.DEBUG),
        'headers': {k: v for k, v in request.META.items() if k.startswith('HTTP_')},
        'remote_addr': request.META.get('REMOTE_ADDR'),
    }
    return JsonResponse(info, json_dumps_params={'indent': 2})

def ping_view(request):
    # Only allow pinging a safe, small whitelist to avoid command injection
    allowed = {'127.0.0.1', 'localhost'}
    host = request.GET.get('host', '127.0.0.1')
    if host not in allowed:
        return HttpResponse('Host not allowed', status=403)

    try:
        proc = subprocess.run(['ping', host], capture_output=True, text=True, timeout=5)
        result = proc.stdout
    except Exception:
        result = 'Ping failed.'
    return HttpResponse(f"<pre>{result}</pre>")

def student_directory(request):
    students = Student.objects.filter(role='student').order_by('full_name')
    instructors = Student.objects.filter(role='instructor').order_by('full_name')

    student_rows = []
    for student in students:
        enrollments = Enrollment.objects.filter(student=student).select_related('course').order_by('course__code')
        student_rows.append({
            'student': student,
            'courses': [enrollment.course for enrollment in enrollments],
        })

    instructor_rows = []
    for instructor in instructors:
        taught_courses = Course.objects.filter(instructor=instructor).order_by('code')
        instructor_rows.append({
            'instructor': instructor,
            'courses': taught_courses,
        })

    return render(request, 'vuln_app/directory.html', {
        'students': student_rows,
        'instructors': instructor_rows,
    })


def stats_courses(request):
    courses = Course.objects.filter(is_active=True).select_related('instructor').order_by('code')
    return render(request, 'vuln_app/stats_courses.html', {'courses': courses})


def stats_learners(request):
    learners = Student.objects.filter(role='student').order_by('full_name')
    return render(request, 'vuln_app/stats_learners.html', {'learners': learners})


def stats_mentors(request):
    mentors = Student.objects.filter(role='instructor').order_by('full_name')
    return render(request, 'vuln_app/stats_mentors.html', {'mentors': mentors})


def stats_completion(request):
    enrollments = Enrollment.objects.select_related('student', 'course').exclude(score=0).exclude(grade='').order_by('-score')
    completed = sum(1 for enrollment in enrollments if float(enrollment.score) >= 60)
    total = enrollments.count()
    rate = round((completed / total) * 100) if total else 0
    return render(request, 'vuln_app/stats_completion.html', {
        'enrollments': enrollments,
        'completed': completed,
        'total': total,
        'rate': rate,
    })


def register(request):
    error = None
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        full_name = request.POST.get('full_name')
        username = request.POST.get('username')
        password = request.POST.get('password') #  Storing as plaintext
        email = request.POST.get('email')

        try:
            # إضافة الطالب لقاعدة البيانات
            # Hash password before storing
            hashed = make_password(password)
            Student.objects.create(
                student_id=student_id,
                full_name=full_name,
                username=username,
                password=hashed,
                email=email,
                role='student'
            )
            return redirect('login')
        except Exception as e:
            error = f"Registration failed: Username or Student ID already exists."
            
    return render(request, 'vuln_app/register.html', {'error': error})