from django.urls import path
from .views import (FrequenciaListView, FrequenciaCreateView,
    FrequenciaUpdateView, FrequenciaDeleteView)

urlpatterns = [
    path('', FrequenciaListView.as_view(),
        name='frequencia_lista'),
    path('nova/', FrequenciaCreateView.as_view(),
        name='frequencia_form'),
    path('<int:pk>/editar/', FrequenciaUpdateView.as_view(),
        name='frequencia_editar' ),
    path('<int:pk>/excluir/',  FrequenciaDeleteView.as_view(),
        name='frequencia_excluir' ),
]