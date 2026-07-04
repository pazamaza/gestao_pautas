from django.contrib import admin

from .models import (
    Encarregado,
    Aluno,
    Matricula
)

admin.site.register(Encarregado)
admin.site.register(Aluno)
admin.site.register(Matricula)