from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Q

from .models import (
    SubdiretorPedagogicoUser,
    AlunoUser,
    EncarregadoUser,
    Perfil,
    ProfessorUser,
    DiretorGeralUser,
    ChefeSecretariaUser,
    CoordenadorTurnoUser,
    CoordenadorPaisUser,
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


@admin.register(SubdiretorPedagogicoUser)
class SubdiretorPedagogicoUserAdmin(GrupoUserAdmin):
    grupo_nome = 'Sub-diretor Pedagógico'
    list_display = ('username', 'first_name', 'last_name', 'email', 'is_active', 'is_superuser')

    def get_queryset(self, request):
        qs = BaseUserAdmin.get_queryset(self, request)
        return qs.filter(Q(groups__name=self.grupo_nome) | Q(is_superuser=True)).distinct()


@admin.register(DiretorGeralUser)
class DiretorGeralUserAdmin(GrupoUserAdmin):
    grupo_nome = 'Diretor Geral do Complexo'
    list_display = ('username', 'first_name', 'last_name', 'email', 'is_active', 'is_superuser')

    def get_queryset(self, request):
        qs = BaseUserAdmin.get_queryset(self, request)
        return qs.filter(Q(groups__name=self.grupo_nome) | Q(is_superuser=True)).distinct()


@admin.register(ChefeSecretariaUser)
class ChefeSecretariaUserAdmin(GrupoUserAdmin):
    grupo_nome = 'Chefe de Secretaria'


@admin.register(CoordenadorTurnoUser)
class CoordenadorTurnoUserAdmin(GrupoUserAdmin):
    grupo_nome = 'Coordenador de Turno'


@admin.register(CoordenadorPaisUser)
class CoordenadorPaisUserAdmin(GrupoUserAdmin):
    grupo_nome = 'Coordenador de Pais e Encarregados de Educação'
