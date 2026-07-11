from django.urls import path
from .views import (FrequenciaListView, FrequenciaCreateView,
    FrequenciaUpdateView, FrequenciaDeleteView,
    JustificacaoListView, justificacao_aprovar, lancamento_frequencia,
    relatorio_assiduidade)

urlpatterns = [
    path('', FrequenciaListView.as_view(),
        name='frequencia_lista'),
    path('lancamento/', lancamento_frequencia,
        name='lancamento_frequencia'),
    path('relatorios/', relatorio_assiduidade,
        name='relatorio_assiduidade'),
    path('nova/', FrequenciaCreateView.as_view(),
        name='frequencia_form'),
    path('<int:pk>/editar/', FrequenciaUpdateView.as_view(),
        name='frequencia_editar' ),
    path('<int:pk>/excluir/',  FrequenciaDeleteView.as_view(),
        name='frequencia_excluir' ),
    path('justificacoes/', JustificacaoListView.as_view(),
        name='justificacao_lista'),
    path('justificacoes/<int:pk>/aprovar/', justificacao_aprovar,
        name='justificacao_aprovar'),
]