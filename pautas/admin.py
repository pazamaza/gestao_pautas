from django.contrib import admin

from .models import (Avaliacao, Nota, Pauta, LinhaPauta,
    ResultadoFinal)
from .models import ResultadoDisciplina

admin.site.register(ResultadoDisciplina)
admin.site.register(Avaliacao)
admin.site.register(Nota)
admin.site.register(Pauta)
admin.site.register(LinhaPauta)
admin.site.register(ResultadoFinal)