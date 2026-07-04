from django.urls import path

from .views import notificacao_lista, notificacao_marcar_lida

urlpatterns = [
    path('', notificacao_lista, name='notificacao_lista'),
    path('<int:pk>/lida/', notificacao_marcar_lida, name='notificacao_marcar_lida'),
]
