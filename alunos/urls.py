from django.urls import path

from .views import ( AlunoListView,
    AlunoCreateView, AlunoUpdateView, AlunoDeleteView,
    AlunoDetailView, EncarregadoListView, EncarregadoCreateView,
    EncarregadoDetailView, EncarregadoUpdateView, EncarregadoDeleteView,)

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
]