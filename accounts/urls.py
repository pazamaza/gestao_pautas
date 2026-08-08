from django.urls import path

from .views import (
    login_view,
    logout_view,
    dashboard,
    perfil,
    AdministradorListView,
    AdministradorCreateView,
    AdministradorDetailView,
    AdministradorUpdateView,
    AdministradorDeleteView,
)

urlpatterns = [

    path(
        'login/',
        login_view,
        name='login'
    ),

    path(
        'logout/',
        logout_view,
        name='logout'
    ),

    path(
        'dashboard/',
        dashboard,
        name='dashboard'
    ),

    path(
        'perfil/',
        perfil,
        name='perfil'
    ),

    path(
        'administradores/',
        AdministradorListView.as_view(),
        name='administrador_lista'
    ),

    path(
        'administradores/novo/',
        AdministradorCreateView.as_view(),
        name='administrador_novo'
    ),

    path(
        'administradores/<int:pk>/',
        AdministradorDetailView.as_view(),
        name='administrador_detalhe'
    ),

    path(
        'administradores/<int:pk>/editar/',
        AdministradorUpdateView.as_view(),
        name='administrador_editar'
    ),

    path(
        'administradores/<int:pk>/excluir/',
        AdministradorDeleteView.as_view(),
        name='administrador_excluir'
    ),
]