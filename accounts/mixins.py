from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render

from .utils import (
    eh_subdiretor_pedagogico,
    eh_admin_ou_professor,
    eh_professor,
    eh_diretor_geral,
    eh_chefe_secretaria,
    eh_coordenador_turno,
    eh_coordenador_pais_encarregados,
)


class AcessoRestritoMixin(LoginRequiredMixin, UserPassesTestMixin):
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return render(self.request, 'dashboards/sem_permissao.html', status=403)


class SubdiretorPedagogicoRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return eh_subdiretor_pedagogico(self.request.user)


class ProfessorRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return eh_professor(self.request.user)


class SuperuserRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return self.request.user.is_superuser


class AdminOuProfessorRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return eh_admin_ou_professor(self.request.user)


class DiretorGeralRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return eh_diretor_geral(self.request.user)


class ChefeSecretariaRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return eh_chefe_secretaria(self.request.user)


class SubdiretorOuSecretariaRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        user = self.request.user
        return eh_subdiretor_pedagogico(user) or eh_chefe_secretaria(user)


class CoordenadorTurnoRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return eh_coordenador_turno(self.request.user)


class CoordenadorPaisRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return eh_coordenador_pais_encarregados(self.request.user)
