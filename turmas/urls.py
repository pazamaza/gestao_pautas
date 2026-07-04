from django.urls import path
from . import views
from .views import (TurmaListView, TurmaCreateView,
    TurmaUpdateView,)

urlpatterns = [

    path('', TurmaListView.as_view(), name='turma_lista'),
    path('novo/', TurmaCreateView.as_view(),  name='turma_novo'),
    path('editar/<int:pk>/', TurmaUpdateView.as_view(), name='turma_editar' ),
    path( "desativar/<int:pk>/",  views.desativar_turma,  name="turma_desativar"),
    path("reativar/<int:pk>/", views.reativar_turma, name="turma_reativar"),
    path("inativas/", views.TurmaInativaListView.as_view(),
    name="turma_inativas")
]