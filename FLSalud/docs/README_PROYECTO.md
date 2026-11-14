# FLSalud — Proyecto de Programación en la Web

## Requisitos cubiertos
- Crear citas médicas generales y asignarlas a un médico disponible.
- Roles: admin, médico, recepcionista y paciente.
- Cita con paciente, médico, duración, fecha, hora y estado.
- Consulta con relación OneToOne a Cita, diagnóstico, síntomas, observaciones y signos vitales.
- Constancia con código único, fecha de admisión, texto, receta e historial médico.
- Login/logout base de Django y permisos por autenticación.
- Agenda, pacientes, consultas y constancias.
- Generación básica de constancia PDF.
- Home HTML/CSS.

## Fuera del alcance
No se implementan especialidades, cirugías, oftalmología, odontología ni otras especialidades, tal como indica el documento.

## Tecnologías
Django + SQLite + HTML/CSS + ReportLab. El proyecto queda preparado para incorporar calendario y correo en una siguiente iteración.

## Puesta en marcha
```bash
python -m venv venv
# Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```
Abrir http://127.0.0.1:8000/
