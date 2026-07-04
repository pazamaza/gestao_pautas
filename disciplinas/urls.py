from django.urls import path

from .views import (
    DisciplinaListView,
    DisciplinaCreateView,
    DisciplinaUpdateView,
    DisciplinaDeleteView,
    DisciplinaDetailView
)

urlpatterns = [

    path(
        '',
        DisciplinaListView.as_view(),
        name='disciplina_lista'
    ),

    path(
        'nova/',
        DisciplinaCreateView.as_view(),
        name='disciplina_nova'
    ),

    path(
        '<int:pk>/',
        DisciplinaDetailView.as_view(),
        name='disciplina_detalhe'
    ),

    path(
        '<int:pk>/editar/',
        DisciplinaUpdateView.as_view(),
        name='disciplina_editar'
    ),

    path(
        '<int:pk>/excluir/',
        DisciplinaDeleteView.as_view(),
        name='disciplina_excluir'
    ),
]