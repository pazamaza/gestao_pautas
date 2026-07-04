from django.urls import path

from .views import (
    TurmaListView,
    TurmaCreateView,
    TurmaUpdateView,
    TurmaDeleteView
)

urlpatterns = [

    path(
        '',
        TurmaListView.as_view(),
        name='turma_lista'
    ),

    path(
        'novo/',
        TurmaCreateView.as_view(),
        name='turma_novo'
    ),

    path(
        'editar/<int:pk>/',
        TurmaUpdateView.as_view(),
        name='turma_editar'
    ),

    path(
        'excluir/<int:pk>/',
        TurmaDeleteView.as_view(),
        name='turma_excluir'
    ),
]