from django.db.models import Avg


def media_turma(queryset):
    return queryset.aggregate( Avg('mt'))

