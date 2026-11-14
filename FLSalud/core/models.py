import uuid

from django.contrib.auth.models import User
from django.db import models


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    medical_history = models.TextField(blank=True)

    def __str__(self):
        if self.user:
            return self.user.get_full_name() or self.user.username
        return f'Paciente #{self.pk}'


class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    professional_id = models.CharField(max_length=50, unique=True)
    available = models.BooleanField(default=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Receptionist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Appointment(models.Model):
    STATUS = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADA', 'Confirmada'),
        ('ATENDIDA', 'Atendida'),
        ('CANCELADA', 'Cancelada'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    duration = models.PositiveIntegerField(default=30)
    status = models.CharField(max_length=20, choices=STATUS, default='PENDIENTE')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'time']


class Consultation(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE)
    diagnosis = models.TextField()
    symptoms = models.TextField()
    observations = models.TextField(blank=True)
    private_notes = models.TextField(blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    blood_pressure = models.CharField(max_length=30, blank=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    prescription = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


def generate_code():
    return uuid.uuid4().hex[:12].upper()


class Certificate(models.Model):
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE)
    unique_code = models.CharField(
        max_length=40, unique=True, default=generate_code, editable=False
    )
    admission_date = models.DateTimeField(auto_now_add=True)
    text = models.TextField()
    recipe = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)

    def __str__(self):
        return self.unique_code


class AccessLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-accessed_at']

    def __str__(self):
        return f'{self.user} -> {self.patient} ({self.accessed_at:%d/%m/%Y %H:%M})'