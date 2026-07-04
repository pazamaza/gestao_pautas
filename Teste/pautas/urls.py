from django.urls import path
from .views import NotaListView
from .views import (NotaListView, pauta_turma)
from .views import (NotaListView, pauta_lancamento)


urlpatterns = [

    path('notas/', NotaListView.as_view(),
        name='nota_lista' ),
        path(
    'turma/<int:turma_id>/', pauta_turma,
    name='pauta_turma'),
    path('lancamento/', pauta_lancamento,
    name='lancamento_notas'),
]