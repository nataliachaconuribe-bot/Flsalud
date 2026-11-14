from django.contrib import admin

from .models import (
    AccessLog,
    Appointment,
    Certificate,
    Consultation,
    Doctor,
    Patient,
    Receptionist,
)

admin.site.register(Patient)
admin.site.register(Doctor)
admin.site.register(Receptionist)
admin.site.register(Appointment)
admin.site.register(Consultation)
admin.site.register(Certificate)


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('accessed_at', 'user', 'patient')
    list_filter = ('user',)
    readonly_fields = ('user', 'patient', 'accessed_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False