from django.core.cache import cache
from django.test import TestCase
from .models import Student, Course, Enrollment


class DashboardViewTests(TestCase):
    def test_dashboard_renders_with_authenticated_session(self):
        Student.objects.create(
            student_id='DEPI-2024-9999',
            full_name='Test Student',
            username='testuser',
            password='secret',
            email='test@example.com',
            role='student',
        )

        session = self.client.session
        session['username'] = 'testuser'
        session['role'] = 'student'
        session['full_name'] = 'Test Student'
        session.save()

        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')

    def test_profile_page_renders_for_authenticated_user(self):
        Student.objects.create(
            student_id='DEPI-2024-1000',
            full_name='Profile Tester',
            username='profileuser',
            password='secret',
            email='profile@example.com',
            role='student',
        )

        session = self.client.session
        session['username'] = 'profileuser'
        session['role'] = 'student'
        session['full_name'] = 'Profile Tester'
        session.save()

        response = self.client.get('/profile/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Profile')

    def test_dashboard_handles_missing_student_record(self):
        session = self.client.session
        session['username'] = 'ghostuser'
        session['role'] = 'student'
        session['full_name'] = 'Ghost User'
        session.save()

        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ghost User')

    def test_login_is_rate_limited_after_repeated_failed_attempts(self):
        cache.clear()

        for _ in range(5):
            response = self.client.post(
                '/login/',
                {'username': 'unknown', 'password': 'wrong'},
                follow=True,
            )
            self.assertEqual(response.status_code, 200)

        blocked_response = self.client.post(
            '/login/',
            {'username': 'unknown', 'password': 'wrong'},
            follow=True,
        )

        self.assertEqual(blocked_response.status_code, 403)

    def test_home_stats_cards_are_clickable_and_show_data(self):
        instructor = Student.objects.create(
            student_id='DEPI-2024-1001',
            full_name='Amr Adel',
            username='amr',
            password='secret',
            email='amr@example.com',
            role='instructor',
        )
        learner = Student.objects.create(
            student_id='DEPI-2024-1002',
            full_name='Sara Ahmed',
            username='sara',
            password='secret',
            email='sara@example.com',
            role='student',
        )
        course = Course.objects.create(
            code='SOC-101',
            title='SOC Analysis',
            description='Hands-on security analysis course',
            instructor=instructor,
            is_active=True,
        )
        Enrollment.objects.create(student=learner, course=course, score=80, grade='A')

        home_response = self.client.get('/')
        self.assertContains(home_response, '/stats/courses/')
        self.assertContains(home_response, '/stats/learners/')
        self.assertContains(home_response, '/stats/mentors/')
        self.assertContains(home_response, '/stats/completion/')

        courses_response = self.client.get('/stats/courses/')
        self.assertContains(courses_response, 'SOC Analysis')

        learners_response = self.client.get('/stats/learners/')
        self.assertContains(learners_response, 'Sara Ahmed')

        mentors_response = self.client.get('/stats/mentors/')
        self.assertContains(mentors_response, 'Amr Adel')

        completion_response = self.client.get('/stats/completion/')
        self.assertContains(completion_response, '100%')

    def test_directory_and_course_details_show_students_and_instructors(self):
        instructor = Student.objects.create(
            student_id='DEPI-2024-2001',
            full_name='Dr. Amr Adel',
            username='amr2',
            password='secret',
            email='amr2@example.com',
            role='instructor',
        )
        student = Student.objects.create(
            student_id='DEPI-2024-2002',
            full_name='Sara Ahmed',
            username='sara2',
            password='secret',
            email='sara2@example.com',
            role='student',
        )
        course = Course.objects.create(
            code='SOC-201',
            title='SOC Analysis',
            description='Security operations course',
            instructor=instructor,
            is_active=True,
        )
        Enrollment.objects.create(student=student, course=course, grade='A', score=90)

        directory_response = self.client.get('/directory/')
        self.assertContains(directory_response, 'Students')
        self.assertContains(directory_response, 'Instructors')
        self.assertContains(directory_response, 'Sara Ahmed')
        self.assertContains(directory_response, 'Dr. Amr Adel')

        course_response = self.client.get('/courses/?id=' + str(course.id))
        self.assertContains(course_response, 'Enrolled Students')
        self.assertContains(course_response, 'Course Instructors')
        self.assertContains(course_response, 'Sara Ahmed')
        self.assertContains(course_response, 'Dr. Amr Adel')

    def test_directory_shows_each_students_courses_with_course_links(self):
        instructor = Student.objects.create(
            student_id='DEPI-2024-3001',
            full_name='Dr. Hoda Magdy',
            username='hoda2',
            password='secret',
            email='hoda2@example.com',
            role='instructor',
        )
        student = Student.objects.create(
            student_id='DEPI-2024-3002',
            full_name='Mostafa Ali',
            username='mostafa',
            password='secret',
            email='mostafa@example.com',
            role='student',
        )
        course = Course.objects.create(
            code='CYB-301',
            title='Threat Hunting',
            description='Advanced threat hunting lab',
            instructor=instructor,
            is_active=True,
        )
        Enrollment.objects.create(student=student, course=course, grade='B', score=75)

        response = self.client.get('/directory/')

        self.assertContains(response, 'Mostafa Ali')
        self.assertContains(response, 'Threat Hunting')
        self.assertContains(response, '/courses/?id=' + str(course.id))
