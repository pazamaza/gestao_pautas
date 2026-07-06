from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Q

from .models import (
    AdministradorUser,
    AlunoUser,
    EncarregadoUser,
    Perfil,
    ProfessorUser,
)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'telefone', 'bi')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'bi')


class GrupoUserAdmin(BaseUserAdmin):
    """Admin de User filtrado por grupo, para separar o cadastro por categoria."""

    grupo_nome = None
    perfil_related_name = None

    list_display = ('username', 'first_name', 'last_name', 'email', 'is_active', 'tem_perfil')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(groups__name=self.grupo_nome).distinct()

    def tem_perfil(self, obj):
        return hasattr(obj, self.perfil_related_name)
    tem_perfil.boolean = True
    tem_perfil.short_description = 'Tem perfil associado'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            grupo, _ = Group.objects.get_or_create(name=self.grupo_nome)
            obj.groups.add(grupo)


@admin.register(ProfessorUser)
class ProfessorUserAdmin(GrupoUserAdmin):
    grupo_nome = 'Professor'
    perfil_related_name = 'professor'


@admin.register(AlunoUser)
class AlunoUserAdmin(GrupoUserAdmin):
    grupo_nome = 'Aluno'
    perfil_related_name = 'aluno'


@admin.register(EncarregadoUser)
class EncarregadoUserAdmin(GrupoUserAdmin):
    grupo_nome = 'Encarregado'
    perfil_related_name = 'encarregado'


@admin.register(AdministradorUser)
class AdministradorUserAdmin(GrupoUserAdmin):
    grupo_nome = 'Administrador'
    list_display = ('username', 'first_name', 'last_name', 'email', 'is_active', 'is_superuser')

    def get_queryset(self, request):
        qs = BaseUserAdmin.get_queryset(self, request)
        return qs.filter(Q(groups__name=self.grupo_nome) | Q(is_superuser=True)).distinct()
