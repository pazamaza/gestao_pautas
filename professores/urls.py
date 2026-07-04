from django.urls import path

from .views import (
    ProfessorListView,
    ProfessorCreateView,
    ProfessorUpdateView,
    ProfessorDeleteView,
    AtribuicaoDocenteListView,
    AtribuicaoDocenteCreateView,
    DiretorTurmaListView,
    DiretorTurmaCreateView,
    DiretorTurmaUpdateView,
)

urlpatterns = [

    path('', ProfessorListView.as_view(),        name='professor_lista' ),

    path('novo/', ProfessorCreateView.as_view(),
        name='professor_novo'),

    path('atribuicoes/', AtribuicaoDocenteListView.as_view(), name='atribuicao_lista'),

    path('atribuicoes/nova/',      AtribuicaoDocenteCreateView.as_view(),      name='atribuicao_nova' ),
    path('<int:pk>/editar/', ProfessorUpdateView.as_view(),
    name='professor_editar'),
    path('<int:pk>/excluir/', ProfessorDeleteView.as_view(),  name='professor_excluir'),

    path('diretores-turma/', DiretorTurmaListView.as_view(), name='diretor_turma_lista'),
    path('diretores-turma/novo/', DiretorTurmaCreateView.as_view(), name='diretor_turma_novo'),
    path('diretores-turma/<int:pk>/editar/', DiretorTurmaUpdateView.as_view(), name='diretor_turma_editar'),
]