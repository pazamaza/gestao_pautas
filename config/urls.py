from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('admin/', admin.site.urls),
    path('turmas/', include('turmas.urls')),
    path('alunos/', include('alunos.urls')),
    path('professores/', include('professores.urls')),
    path('disciplinas/', include('disciplinas.urls')),
    path('pautas/', include('pautas.urls')),
    path('frequencias/', include('frequencias.urls')),
    path('notificacoes/', include('notificacoes.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)