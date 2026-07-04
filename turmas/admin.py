from django.contrib import admin

from .models import (
    AnoLetivo,
    PeriodoAcademico,
    Classe,
    Turma
)

admin.site.register(AnoLetivo)
admin.site.register(PeriodoAcademico)
admin.site.register(Classe)
admin.site.register(Turma)