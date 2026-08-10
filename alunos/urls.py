from django.urls import path

from .views import ( AlunoListView,
    AlunoCreateView, AlunoUpdateView, AlunoDeleteView,
    AlunoDetailView, EncarregadoListView, EncarregadoCreateView,
    EncarregadoDetailView, EncarregadoUpdateView, EncarregadoDeleteView,
    ReclamacaoListView, ReclamacaoCreateView, ReclamacaoDetailView,
    reclamacao_encaminhar, reclamacao_resolver,)

urlpatterns = [

    path('', AlunoListView.as_view(),     name='aluno_lista' ),

    path('novo/', AlunoCreateView.as_view(),
        name='aluno_novo'),

    path('<int:pk>/', AlunoDetailView.as_view(),
        name='aluno_detalhe'),

    path('editar/<int:pk>/', AlunoUpdateView.as_view(),
        name='aluno_editar'),

    path('excluir/<int:pk>/', AlunoDeleteView.as_view(),
        name='aluno_excluir'),
    path('encarregados/', EncarregadoListView.as_view(),
    name='encarregado_lista'),
    path('encarregados/novo/', EncarregadoCreateView.as_view(),name='encarregado_novo'),
    path('encarregados/<int:pk>/', EncarregadoDetailView.as_view(),
        name='encarregado_detalhe'),
    path('encarregados/<int:pk>/editar/', EncarregadoUpdateView.as_view(),
        name='encarregado_editar'),
    path('encarregados/<int:pk>/excluir/', EncarregadoDeleteView.as_view(),
        name='encarregado_excluir'),

    path('reclamacoes/', ReclamacaoListView.as_view(), name='reclamacao_lista'),
    path('reclamacoes/nova/', ReclamacaoCreateView.as_view(), name='reclamacao_nova'),
    path('reclamacoes/<int:pk>/', ReclamacaoDetailView.as_view(), name='reclamacao_detalhe'),
    path('reclamacoes/<int:pk>/encaminhar/', reclamacao_encaminhar, name='reclamacao_encaminhar'),
    path('reclamacoes/<int:pk>/resolver/', reclamacao_resolver, name='reclamacao_resolver'),
]