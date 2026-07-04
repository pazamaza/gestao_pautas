from django.urls import path

from .views import ( AlunoListView,
    AlunoCreateView, AlunoUpdateView, AlunoDeleteView,
    AlunoDetailView, EncarregadoListView,EncarregadoCreateView,)

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
]