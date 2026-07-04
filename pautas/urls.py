from django.urls import path

from .views import (
    AvaliacaoCreateView,
    AvaliacaoDeleteView,
    AvaliacaoListView,
    AvaliacaoUpdateView,
    NotaCreateView,
    NotaDeleteView,
    NotaListView,
    NotaUpdateView,
    ResultadoDisciplinaCreateView,
    ResultadoDisciplinaDeleteView,
    ResultadoDisciplinaListView,
    ResultadoDisciplinaUpdateView,
    baixar_modelo_excel,
    exportar_excel,
    exportar_pdf,
    gerar_resultados,
    importar_excel,
    pauta_trimestral,
    pauta_turma,
)


urlpatterns = [
    path('notas/', NotaListView.as_view(), name='nota_lista'),
    path('turma/<int:turma_id>/', pauta_turma, name='pauta_turma'),
    path('nova/', NotaCreateView.as_view(), name='nota_nova'),
    path('<int:pk>/editar/', NotaUpdateView.as_view(), name='nota_editar'),
    path('<int:pk>/excluir/', NotaDeleteView.as_view(), name='nota_excluir'),

    path('avaliacoes/', AvaliacaoListView.as_view(), name='avaliacao_lista'),
    path('avaliacoes/nova/', AvaliacaoCreateView.as_view(), name='avaliacao_nova'),
    path('avaliacoes/<int:pk>/editar/', AvaliacaoUpdateView.as_view(), name='avaliacao_editar'),
    path('avaliacoes/<int:pk>/excluir/', AvaliacaoDeleteView.as_view(), name='avaliacao_excluir'),
    path('avaliacoes/<int:avaliacao_id>/pauta/', pauta_trimestral, name='pauta_trimestral'),
    path('avaliacoes/<int:avaliacao_id>/modelo-excel/', baixar_modelo_excel, name='pauta_modelo_excel'),
    path('avaliacoes/<int:avaliacao_id>/importar-excel/', importar_excel, name='pauta_importar_excel'),
    path('avaliacoes/<int:avaliacao_id>/exportar-excel/', exportar_excel, name='pauta_exportar_excel'),
    path('avaliacoes/<int:avaliacao_id>/exportar-pdf/', exportar_pdf, name='pauta_exportar_pdf'),

    path('resultados/', ResultadoDisciplinaListView.as_view(), name='resultado_lista'),
    path('resultados/novo/', ResultadoDisciplinaCreateView.as_view(), name='resultado_novo'),
    path('resultados/<int:pk>/editar/', ResultadoDisciplinaUpdateView.as_view(), name='resultado_editar'),
    path('resultados/<int:pk>/excluir/', ResultadoDisciplinaDeleteView.as_view(), name='resultado_excluir'),
    path('resultados/gerar/', gerar_resultados, name='gerar_resultados'),
]
