from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render

from .utils import eh_administrador, eh_admin_ou_professor, eh_professor


class AcessoRestritoMixin(LoginRequiredMixin, UserPassesTestMixin):
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        return render(self.request, 'dashboards/sem_permissao.html', status=403)


class AdministradorRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return eh_administrador(self.request.user)


class ProfessorRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return eh_professor(self.request.user)


class SuperuserRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return self.request.user.is_superuser


class AdminOuProfessorRequeridoMixin(AcessoRestritoMixin):
    def test_func(self):
        return eh_admin_ou_professor(self.request.user)
