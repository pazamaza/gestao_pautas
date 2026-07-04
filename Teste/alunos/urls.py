from django.urls import path

from .views import (
    AlunoListView,
    AlunoCreateView,
    AlunoUpdateView,
    AlunoDeleteView,
    AlunoDetailView
)

urlpatterns = [

    path(
        '',
        AlunoListView.as_view(),
        name='aluno_lista'
    ),

    path(
        'novo/',
        AlunoCreateView.as_view(),
        name='aluno_novo'
    ),

    path(
        '<int:pk>/',
        AlunoDetailView.as_view(),
        name='aluno_detalhe'
    ),

    path(
        'editar/<int:pk>/',
        AlunoUpdateView.as_view(),
        name='aluno_editar'
    ),

    path(
        'excluir/<int:pk>/',
        AlunoDeleteView.as_view(),
        name='aluno_excluir'
    ),
]