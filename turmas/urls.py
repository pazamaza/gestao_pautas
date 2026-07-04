from django.urls import path
from . import views
from .views import (TurmaListView, TurmaCreateView,
    TurmaUpdateView, PeriodoAcademicoListView, PeriodoAcademicoCreateView,
    PeriodoAcademicoUpdateView,)

urlpatterns = [

    path('', TurmaListView.as_view(), name='turma_lista'),
    path('novo/', TurmaCreateView.as_view(),  name='turma_novo'),
    path('editar/<int:pk>/', TurmaUpdateView.as_view(), name='turma_editar' ),
    path( "desativar/<int:pk>/",  views.desativar_turma,  name="turma_desativar"),
    path("reativar/<int:pk>/", views.reativar_turma, name="turma_reativar"),
    path("inativas/", views.TurmaInativaListView.as_view(),
    name="turma_inativas"),

    path('periodos/', PeriodoAcademicoListView.as_view(), name='periodo_lista'),
    path('periodos/novo/', PeriodoAcademicoCreateView.as_view(), name='periodo_novo'),
    path('periodos/<int:pk>/editar/', PeriodoAcademicoUpdateView.as_view(), name='periodo_editar'),
]