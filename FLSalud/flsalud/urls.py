from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path

from core import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('citas/', views.appointments, name='appointments'),
    path('citas/nueva/', views.create_appointment, name='create_appointment'),
    path('citas/disponibilidad/', views.availability, name='availability'),
    path('citas/<int:pk>/atendida/', views.mark_attended, name='mark_attended'),
    path('citas/<int:pk>/confirmar/', views.confirm_appointment, name='confirm_appointment'),

    path('pacientes/', views.patients, name='patients'),
    path('pacientes/<int:pk>/', views.patient_detail, name='patient_detail'),

    path('consultas/', views.consultations, name='consultations'),
    path('consultas/<int:pk>/constancia/', views.create_certificate, name='create_certificate'),

    path('constancias/', views.certificates, name='certificates'),
    path('constancias/<int:pk>/pdf/', views.certificate_pdf, name='certificate_pdf'),

    path('perfil/', views.profile, name='profile'),
]