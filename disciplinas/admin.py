from django.contrib import admin
from .models import Disciplina


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sigla', 'nuclear', 'ativa')
    list_filter = ('nuclear', 'ativa')
    search_fields = ('nome', 'sigla')
