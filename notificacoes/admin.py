from django.contrib import admin

from .models import Notificacao


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'destinatario', 'nivel', 'lida', 'criado_em')
    list_filter = ('nivel', 'lida')
    search_fields = ('titulo', 'destinatario__username', 'destinatario__first_name', 'destinatario__last_name')
