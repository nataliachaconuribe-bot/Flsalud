from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

from .forms import AppointmentForm, ConsultationForm, SLOT_MINUTES, WORK_END, WORK_START
from .models import AccessLog, Appointment, Certificate, Consultation, Doctor, Patient

PAGE_SIZE = 10



def get_role(user):
    if user.is_superuser:
        return 'admin'
    for role in ('doctor', 'receptionist', 'patient'):
        if hasattr(user, role):
            return role
    if user.is_staff:
        return 'staff'
    return None


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if get_role(request.user) not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def _appointments_for(user):
    role = get_role(user)
    qs = Appointment.objects.select_related('patient__user', 'doctor__user')

    if role in ('admin', 'receptionist', 'staff'):
        return qs
    if role == 'doctor':
        return qs.filter(doctor__user=user)
    if role == 'patient':
        return qs.filter(patient__user=user)
    return qs.none()


def _certificates_for(user):
    role = get_role(user)
    qs = Certificate.objects.select_related('consultation__appointment__patient__user')

    if role == 'admin':
        return qs
    if role == 'doctor':
        return qs.filter(
            consultation__appointment__patient__appointment__doctor__user=user
        ).distinct()
    if role == 'patient':
        return qs.filter(consultation__appointment__patient__user=user)
    return qs.none()


def home(request):
    return render(request, 'core/home.html')


def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user:
            login(request, user)
            return redirect('dashboard')
        messages.error(request, 'Usuario o contraseña incorrectos.')
    return render(request, 'core/login.html')


@login_required
def dashboard(request):
    today = timezone.localdate()
    context = {
        'today': today,
        'appointments': _appointments_for(request.user).filter(date=today),
    }

    if get_role(request.user) in ('admin', 'receptionist'):
        context.update({
            'patients': Patient.objects.count(),
            'consultations': Consultation.objects.count(),
            'certificates': Certificate.objects.count(),
        })

    return render(request, 'core/dashboard.html', context)


@login_required
def appointments(request):
    qs = _appointments_for(request.user)

    if get_role(request.user) == 'staff':
        qs = qs.filter(date=timezone.localdate())

    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get('page'))
    return render(request, 'core/appointments.html', {'appointments': page})


@role_required('admin', 'receptionist')
def create_appointment(request):
    form = AppointmentForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Cita registrada correctamente.')
        return redirect('appointments')
    return render(request, 'core/form.html', {'form': form, 'title': 'Nueva cita'})


def _free_slots(doctor, day):
    busy = Appointment.objects.filter(doctor=doctor, date=day).exclude(status='CANCELADA')
    intervals = []
    for a in busy:
        start = datetime.combine(day, a.time)
        intervals.append((start, start + timedelta(minutes=a.duration)))

    slots = []
    step = timedelta(minutes=SLOT_MINUTES)
    cursor = datetime.combine(day, WORK_START)
    end = datetime.combine(day, WORK_END)
    while cursor + step <= end:
        slot_end = cursor + step
        if not any(cursor < b_end and b_start < slot_end for b_start, b_end in intervals):
            slots.append(cursor.time())
        cursor = slot_end
    return slots


@role_required('admin', 'receptionist')
def availability(request):
    raw = request.GET.get('date')
    try:
        day = datetime.strptime(raw, '%Y-%m-%d').date() if raw else timezone.localdate()
    except ValueError:
        day = timezone.localdate()

    rows = []
    for doctor in Doctor.objects.filter(available=True).select_related('user'):
        rows.append({
            'doctor': doctor,
            'appointments': Appointment.objects.filter(doctor=doctor, date=day)
                .exclude(status='CANCELADA')
                .select_related('patient__user'),
            'free': _free_slots(doctor, day),
        })

    return render(request, 'core/availability.html', {'rows': rows, 'day': day})


@require_POST
@role_required('admin', 'receptionist')
def mark_attended(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if appt.status != 'CONFIRMADA':
        messages.error(request, 'Solo se pueden marcar como atendidas las citas confirmadas.')
    else:
        appt.status = 'ATENDIDA'
        appt.save(update_fields=['status'])
        messages.success(request, 'Cita marcada como atendida.')
    return redirect('appointments')

@require_POST
@role_required('admin', 'receptionist')
def confirm_appointment(request, pk):
    appt = get_object_or_404(Appointment, pk=pk)
    if appt.status != 'PENDIENTE':
        messages.error(request, 'Solo se pueden confirmar las citas pendientes.')
    else:
        appt.status = 'CONFIRMADA'
        appt.save(update_fields=['status'])
        messages.success(request, 'Cita confirmada correctamente.')
    return redirect('appointments')


@role_required('admin', 'doctor', 'receptionist')
def patients(request):
    qs = Patient.objects.select_related('user').order_by('id')

    if get_role(request.user) == 'doctor':
        qs = qs.filter(appointment__doctor__user=request.user).distinct()

    page = Paginator(qs, PAGE_SIZE).get_page(request.GET.get('page'))
    return render(request, 'core/patients.html', {'patients': page})


@role_required('admin', 'doctor')
def patient_detail(request, pk):
    patients_qs = Patient.objects.select_related('user')

    if get_role(request.user) == 'doctor':
        patients_qs = patients_qs.filter(appointment__doctor__user=request.user).distinct()

    patient = get_object_or_404(patients_qs, pk=pk)

    AccessLog.objects.create(user=request.user, patient=patient)

    pending = Appointment.objects.filter(
        patient=patient,
        status__in=['PENDIENTE', 'CONFIRMADA'],
    ).select_related('doctor__user')

    history = Consultation.objects.filter(
        appointment__patient=patient
    ).select_related(
        'appointment__doctor__user', 'certificate'
    ).order_by('-appointment__date', '-appointment__time')

    return render(request, 'core/patient_detail.html', {
        'patient': patient,
        'pending': pending,
        'history': history,
    })


@role_required('admin', 'doctor')
def consultations(request):
    role = get_role(request.user)
    form = ConsultationForm(request.POST or None, user=request.user)

    if form.is_valid():
        c = form.save()
        Appointment.objects.filter(pk=c.appointment_id).update(status='ATENDIDA')
        messages.success(request, 'Consulta registrada correctamente.')
        return redirect('consultations')

    qs = Consultation.objects.select_related(
        'appointment__patient__user',
        'appointment__doctor__user',
        'certificate',
    )
    if role == 'doctor':
        qs = qs.filter(appointment__doctor__user=request.user)

    return render(request, 'core/consultations.html', {
        'consultations': qs,
        'form': form,
    })


@login_required
def certificates(request):
    return render(request, 'core/certificates.html', {
        'certificates': _certificates_for(request.user)
    })


@require_POST
@role_required('admin', 'doctor')
def create_certificate(request, pk):
    consultations_qs = Consultation.objects.select_related(
        'appointment__patient__user', 'appointment__doctor__user'
    )
    if get_role(request.user) == 'doctor':
        consultations_qs = consultations_qs.filter(
            appointment__doctor__user=request.user
        )

    consultation = get_object_or_404(consultations_qs, pk=pk)
    appt = consultation.appointment

    cert, created = Certificate.objects.get_or_create(
        consultation=consultation,
        defaults={
            'text': (
                f'Se hace constar que {appt.patient} fue atendido(a) en consulta '
                f'médica general el {appt.date:%d/%m/%Y} por el/la Dr(a). '
                f'{appt.doctor}. Diagnóstico: {consultation.diagnosis}'
            ),
            'recipe': consultation.prescription,
            'medical_history': appt.patient.medical_history,
        },
    )

    if created:
        messages.success(request, f'Constancia {cert.unique_code} generada correctamente.')
    else:
        messages.info(request, 'Esta consulta ya tenía una constancia.')

    return redirect('certificates')


@login_required
def certificate_pdf(request, pk):
    cert = get_object_or_404(_certificates_for(request.user), pk=pk)
    buf = BytesIO()
    p = canvas.Canvas(buf)
    p.setTitle('Constancia FLSalud')

    p.setFont('Helvetica-Bold', 16)
    p.drawString(72, 780, 'FLSalud - Constancia médica')

    p.setFont('Helvetica', 11)
    p.drawString(72, 750, f'Código: {cert.unique_code}')
    p.drawString(72, 732, f'Paciente: {cert.consultation.appointment.patient}')
    p.drawString(72, 714, f'Fecha: {cert.admission_date:%d/%m/%Y}')

    y = 680
    for line in simpleSplit(cert.text, 'Helvetica', 11, 450):
        p.drawString(72, y, line)
        y -= 16

    if cert.recipe:
        y -= 14
        p.setFont('Helvetica-Bold', 11)
        p.drawString(72, y, 'Indicaciones / Receta:')
        p.setFont('Helvetica', 11)
        y -= 16
        for line in simpleSplit(cert.recipe, 'Helvetica', 11, 450):
            p.drawString(72, y, line)
            y -= 16

    p.save()
    buf.seek(0)
    return HttpResponse(buf.read(), content_type='application/pdf')


@login_required
def profile(request):
    return render(request, 'core/profile.html', {'user': request.user})