from django.contrib import admin

from .models import Escola


@admin.register(Escola)
class EscolaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'administracao_municipal', 'nome_autoridade_visto', 'cargo_autoridade_visto')
    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'logotipo')
        }),
        ('Hierarquia Institucional', {
            'fields': ('ministerio', 'governo_provincial', 'administracao_municipal')
        }),
        ('Visto', {
            'fields': ('nome_autoridade_visto', 'cargo_autoridade_visto')
        }),
    )

    def has_add_permission(self, request):
        if Escola.objects.exists():
            return False
        return super().has_add_permission(request)
