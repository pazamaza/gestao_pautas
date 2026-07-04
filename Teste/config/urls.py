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
]