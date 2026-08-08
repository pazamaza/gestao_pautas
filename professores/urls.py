from django.urls import path

from .views import (
    ProfessorListView,
    ProfessorCreateView,
    ProfessorUpdateView,
    ProfessorDeleteView,
    ProfessorDetailView,
    AtribuicaoDocenteListView,
    AtribuicaoDocenteCreateView,
    AtribuicaoDocenteDetailView,
    AtribuicaoDocenteUpdateView,
    atribuicao_desativar,
    atribuicao_reativar,
    DiretorTurmaListView,
    DiretorTurmaCreateView,
    DiretorTurmaUpdateView,
    DiretorTurmaDetailView,
    DiretorTurmaDeleteView,
)

urlpatterns = [

    path('', ProfessorListView.as_view(),        name='professor_lista' ),

    path('novo/', ProfessorCreateView.as_view(),
        name='professor_novo'),

    path('atribuicoes/', AtribuicaoDocenteListView.as_view(), name='atribuicao_lista'),

    path('atribuicoes/nova/',      AtribuicaoDocenteCreateView.as_view(),      name='atribuicao_nova' ),
    path('atribuicoes/<int:pk>/', AtribuicaoDocenteDetailView.as_view(), name='atribuicao_detalhe'),
    path('atribuicoes/<int:pk>/editar/', AtribuicaoDocenteUpdateView.as_view(), name='atribuicao_editar'),
    path('atribuicoes/<int:pk>/desativar/', atribuicao_desativar, name='atribuicao_desativar'),
    path('atribuicoes/<int:pk>/reativar/', atribuicao_reativar, name='atribuicao_reativar'),

    path('<int:pk>/', ProfessorDetailView.as_view(), name='professor_detalhe'),
    path('<int:pk>/editar/', ProfessorUpdateView.as_view(),
    name='professor_editar'),
    path('<int:pk>/excluir/', ProfessorDeleteView.as_view(),  name='professor_excluir'),

    path('diretores-turma/', DiretorTurmaListView.as_view(), name='diretor_turma_lista'),
    path('diretores-turma/novo/', DiretorTurmaCreateView.as_view(), name='diretor_turma_novo'),
    path('diretores-turma/<int:pk>/', DiretorTurmaDetailView.as_view(), name='diretor_turma_detalhe'),
    path('diretores-turma/<int:pk>/editar/', DiretorTurmaUpdateView.as_view(), name='diretor_turma_editar'),
    path('diretores-turma/<int:pk>/excluir/', DiretorTurmaDeleteView.as_view(), name='diretor_turma_excluir'),
]