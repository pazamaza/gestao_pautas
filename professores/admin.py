from django.contrib import admin
from .models import Professor, AtribuicaoDocente, DiretorTurma

admin.site.register(Professor)
admin.site.register(AtribuicaoDocente)
admin.site.register(DiretorTurma)