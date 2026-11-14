from datetime import datetime, time as dtime, timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Appointment, Consultation, Doctor

WORK_START = dtime(8, 0)
WORK_END = dtime(17, 0)
SLOT_MINUTES = 30


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'date', 'time', 'duration', 'status']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['doctor'].queryset = Doctor.objects.filter(
            available=True
        ).select_related('user')

    @staticmethod
    def _overlaps(start, end, other):
        other_start = datetime.combine(other.date, other.time)
        other_end = other_start + timedelta(minutes=other.duration)
        return start < other_end and other_start < end

    def clean(self):
        cleaned = super().clean()

        patient = cleaned.get('patient')
        doctor = cleaned.get('doctor')
        date = cleaned.get('date')
        time = cleaned.get('time')
        duration = cleaned.get('duration')
        status = cleaned.get('status')

        if not all([patient, doctor, date, time, duration]):
            return cleaned

        if status == 'CANCELADA':
            return cleaned

        if duration < 5:
            self.add_error('duration', 'La duración mínima es de 5 minutos.')

        if not self.instance.pk and date < timezone.localdate():
            self.add_error('date', 'No se puede agendar una cita en una fecha pasada.')

        start = datetime.combine(date, time)
        end = start + timedelta(minutes=duration)

        if time < WORK_START or end > datetime.combine(date, WORK_END):
            raise ValidationError(
                f'El horario de atención es de {WORK_START:%H:%M} a {WORK_END:%H:%M}.'
            )

        same_day = Appointment.objects.filter(date=date).exclude(status='CANCELADA')
        if self.instance.pk:
            same_day = same_day.exclude(pk=self.instance.pk)

        for other in same_day.filter(doctor=doctor):
            if self._overlaps(start, end, other):
                raise ValidationError(
                    f'El médico ya tiene una cita a las {other.time:%H:%M} '
                    f'({other.duration} min) que se cruza con este horario.'
                )

        for other in same_day.filter(patient=patient):
            if self._overlaps(start, end, other):
                raise ValidationError(
                    f'El paciente ya tiene una cita a las {other.time:%H:%M} '
                    f'que se cruza con este horario.'
                )

        return cleaned


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = [
            'appointment', 'diagnosis', 'symptoms', 'observations', 'private_notes',
            'weight', 'blood_pressure', 'temperature', 'prescription',
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        qs = Appointment.objects.filter(
            status__in=['PENDIENTE', 'CONFIRMADA'],
            consultation__isnull=True,
        ).select_related('patient__user', 'doctor__user')

        if user is not None and not user.is_superuser:
            qs = qs.filter(doctor__user=user)

        self.fields['appointment'].queryset = qs
        self.fields['appointment'].label_from_instance = lambda a: (
            f'{a.date:%d/%m/%Y} {a.time:%H:%M} · {a.patient} (Dr. {a.doctor})'
        )
        self.fields['private_notes'].label = 'Nota reservada (solo la ve usted)'