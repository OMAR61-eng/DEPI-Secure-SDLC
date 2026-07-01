from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('',                           views.home,             name='home'),
    path('login/',                     views.login_view,       name='login'),
    path('register/',                  views.register,         name='register'), 
    path('logout/',                    views.logout_view,      name='logout'),
    path('search/',                    views.search,           name='search'),
    path('courses/',                   views.course_detail,    name='course_detail'),
    path('directory/',                 views.student_directory,name='directory'),
    
    # Authenticated
    path('dashboard/',                 views.dashboard,        name='dashboard'),
    path('grades/',                    views.my_grades,        name='my_grades'),
    path('grades/<int:enrollment_id>/',views.grades,           name='grades'),
    path('announcements/',             views.announcements,    name='announcements'),
    path('tickets/',                   views.tickets,          name='tickets'),
    path('tickets/<int:ticket_id>/',   views.ticket_detail,    name='ticket_detail'),
    path('profile/',                   views.profile_page,     name='profile_page'),
    path('stats/courses/',             views.stats_courses,    name='stats_courses'),
    path('stats/learners/',            views.stats_learners,   name='stats_learners'),
    path('stats/mentors/',             views.stats_mentors,    name='stats_mentors'),
    path('stats/completion/',          views.stats_completion, name='stats_completion'),
    
    # API / Misconfiguration endpoints
    path('api/profile/<str:student_id>/', views.profile_api,   name='profile_api'),
    path('api/debug/',                 views.debug_info,       name='debug_info'),
    path('ping/',                     views.ping_view,       name='ping'),
]