import datetime
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from alunos.models import Aluno, Encarregado
from disciplinas.models import Disciplina
from frequencias.models import Frequencia
from notificacoes.models import Notificacao
from professores.models import AtribuicaoDocente, DiretorTurma, Professor
from turmas.models import AnoLetivo, Classe, HorarioAula, PeriodoAcademico, Turma

from .models import Avaliacao, Nota, ResultadoDisciplina, SituacaoAnual
from .services.resultados import montar_pauta_final_turma, verificar_transicao_aluno


class PautasTestBase(TestCase):
    def setUp(self):
        self.grupo_admin, _ = Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        self.grupo_professor, _ = Group.objects.get_or_create(name='Professor')

        self.admin_user = User.objects.create_user(username='admin', password='senha123')
        self.admin_user.groups.add(self.grupo_admin)

        self.professor_user = User.objects.create_user(username='prof', password='senha123')
        self.professor_user.groups.add(self.grupo_professor)
        self.professor = Professor.objects.create(
            user=self.professor_user, numero_funcionario='P001'
        )

        self.outro_professor_user = User.objects.create_user(username='outro_prof', password='senha123')
        self.outro_professor_user.groups.add(self.grupo_professor)
        self.outro_professor = Professor.objects.create(
            user=self.outro_professor_user, numero_funcionario='P002'
        )

        self.ano_letivo = AnoLetivo.objects.create(descricao='2026')
        self.classe, _ = Classe.objects.get_or_create(nome='7ª Classe')
        self.turma = Turma.objects.create(nome='A', classe=self.classe, ano_letivo=self.ano_letivo)
        self.disciplina = Disciplina.objects.create(nome='Matemática', sigla='MAT')

        self.periodo = PeriodoAcademico.objects.create(
            nome='1º Trimestre', ano_letivo=self.ano_letivo, aberto=True
        )

        self.atribuicao = AtribuicaoDocente.objects.create(
            professor=self.professor,
            disciplina=self.disciplina,
            turma=self.turma,
            ano_letivo=self.ano_letivo,
        )

        self.avaliacao = Avaliacao.objects.create(
            atribuicao=self.atribuicao, periodo=self.periodo
        )

        encarregado_user = User.objects.create_user(username='encarregado1', password='senha123')
        self.encarregado = Encarregado.objects.create(user=encarregado_user, telefone='900000000')
        self.aluno = Aluno.objects.create(
            nome='Aluno Teste',
            numero_processo='NP001',
            data_nascimento=datetime.date(2010, 1, 1),
            sexo='M',
            turma=self.turma,
            encarregado=self.encarregado,
        )

        self.nota = Nota.objects.create(
            avaliacao=self.avaliacao, aluno=self.aluno, mac=10, npt=10
        )


class PeriodoLancamentoTests(PautasTestBase):
    def test_nota_form_bloqueia_fora_do_periodo(self):
        self.periodo.aberto = False
        self.periodo.save()

        self.client.login(username='prof', password='senha123')
        response = self.client.post(
            reverse('nota_editar', args=[self.nota.pk]),
            {
                'avaliacao': self.avaliacao.pk,
                'aluno': self.aluno.pk,
                'mac': 15,
                'npt': 15,
                'observacao': '',
            },
        )

        self.nota.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.nota.mac, 10)

    def test_nota_form_permite_dentro_do_periodo(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.post(
            reverse('nota_editar', args=[self.nota.pk]),
            {
                'avaliacao': self.avaliacao.pk,
                'aluno': self.aluno.pk,
                'mac': 15,
                'npt': 15,
                'observacao': '',
            },
        )

        self.nota.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.nota.mac, 15)


class ValidacaoAvaliacaoTests(PautasTestBase):
    def test_admin_valida_avaliacao(self):
        self.client.login(username='admin', password='senha123')
        response = self.client.get(reverse('avaliacao_validar', args=[self.avaliacao.pk]))

        self.avaliacao.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.avaliacao.status, Avaliacao.STATUS_VALIDADA)
        self.assertEqual(self.avaliacao.validado_por, self.admin_user)

    def test_admin_reporta_erro_notifica_professor_e_diretor(self):
        DiretorTurma.objects.create(
            professor=self.outro_professor, turma=self.turma, ano_letivo=self.ano_letivo
        )

        self.client.login(username='admin', password='senha123')
        response = self.client.post(
            reverse('avaliacao_reportar_erro', args=[self.avaliacao.pk]),
            {'observacoes_validacao': 'Nota do aluno X está incorreta.'},
        )

        self.avaliacao.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.avaliacao.status, Avaliacao.STATUS_COM_ERROS)

        destinatarios = set(
            Notificacao.objects.values_list('destinatario__username', flat=True)
        )
        self.assertIn('prof', destinatarios)
        self.assertIn('outro_prof', destinatarios)

    def test_professor_nao_acede_a_validar(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.get(reverse('avaliacao_validar', args=[self.avaliacao.pk]))
        self.assertEqual(response.status_code, 403)


class DiretorTurmaVisualizaPautaTests(PautasTestBase):
    def setUp(self):
        super().setUp()
        DiretorTurma.objects.create(
            professor=self.outro_professor, turma=self.turma, ano_letivo=self.ano_letivo
        )

    def test_diretor_de_turma_ve_pauta_de_outra_disciplina(self):
        self.client.login(username='outro_prof', password='senha123')
        response = self.client.get(reverse('pauta_trimestral', args=[self.avaliacao.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Importar Notas')
        self.assertContains(response, 'diretor de turma')

    def test_diretor_de_turma_nao_pode_importar_notas(self):
        self.client.login(username='outro_prof', password='senha123')
        response = self.client.post(
            reverse('pauta_importar_excel', args=[self.avaliacao.pk]), {}
        )
        self.assertEqual(response.status_code, 403)

    def test_professor_sem_relacao_com_a_turma_nao_ve_pauta(self):
        terceiro_user = User.objects.create_user(username='terceiro_prof', password='senha123')
        terceiro_user.groups.add(self.grupo_professor)
        Professor.objects.create(user=terceiro_user, numero_funcionario='P003')

        self.client.login(username='terceiro_prof', password='senha123')
        response = self.client.get(reverse('pauta_trimestral', args=[self.avaliacao.pk]))
        self.assertEqual(response.status_code, 403)


class PermissoesPautasTests(PautasTestBase):
    def test_admin_nao_acede_a_criar_nota(self):
        self.client.login(username='admin', password='senha123')
        response = self.client.get(reverse('nota_nova'))
        self.assertEqual(response.status_code, 403)

    def test_professor_acede_a_criar_nota(self):
        self.client.login(username='prof', password='senha123')
        response = self.client.get(reverse('nota_nova'))
        self.assertEqual(response.status_code, 200)

    def test_resultado_disciplina_edicao_requer_superuser(self):
        self.client.login(username='admin', password='senha123')
        response = self.client.get(reverse('resultado_novo'))
        self.assertEqual(response.status_code, 403)

        self.admin_user.is_superuser = True
        self.admin_user.save()
        response = self.client.get(reverse('resultado_novo'))
        self.assertEqual(response.status_code, 200)

    def test_anonimo_redirecionado_para_login(self):
        response = self.client.get(reverse('avaliacao_lista'))
        self.assertEqual(response.status_code, 302)


class ConsultaPautasTests(PautasTestBase):
    def setUp(self):
        super().setUp()

        grupo_aluno, _ = Group.objects.get_or_create(name='Aluno')
        grupo_encarregado, _ = Group.objects.get_or_create(name='Encarregado')

        self.aluno_user = User.objects.create_user(username='aluno1', password='senha123')
        self.aluno_user.groups.add(grupo_aluno)
        self.aluno.user = self.aluno_user
        self.aluno.save()

        self.encarregado_user = self.encarregado.user
        self.encarregado_user.groups.add(grupo_encarregado)

        self.avaliacao.status = Avaliacao.STATUS_VALIDADA
        self.avaliacao.save()

        outro_periodo = PeriodoAcademico.objects.create(
            nome='2º Trimestre', ano_letivo=self.ano_letivo, aberto=True
        )
        self.avaliacao_com_erros = Avaliacao.objects.create(
            atribuicao=self.atribuicao, periodo=outro_periodo, status=Avaliacao.STATUS_COM_ERROS
        )
        Nota.objects.create(
            avaliacao=self.avaliacao_com_erros, aluno=self.aluno, mac=5, npt=5
        )

        outro_encarregado_user = User.objects.create_user(username='encarregado2', password='senha123')
        outro_encarregado_user.groups.add(grupo_encarregado)
        self.outro_encarregado = Encarregado.objects.create(
            user=outro_encarregado_user, telefone='911111111'
        )
        self.outro_aluno = Aluno.objects.create(
            nome='Outro Aluno',
            numero_processo='NP002',
            data_nascimento=datetime.date(2011, 2, 2),
            sexo='F',
            turma=self.turma,
            encarregado=self.outro_encarregado,
        )

    def test_aluno_ve_apenas_notas_validadas(self):
        self.client.login(username='aluno1', password='senha123')
        response = self.client.get(reverse('minhas_notas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1º Trimestre')
        self.assertNotContains(response, '2º Trimestre')

    def test_aluno_sem_registo_associado_ve_mensagem_amigavel(self):
        sem_registo = User.objects.create_user(username='sem_registo', password='senha123')
        sem_registo.groups.add(Group.objects.get(name='Aluno'))

        self.client.login(username='sem_registo', password='senha123')
        response = self.client.get(reverse('minhas_notas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'não está associada a um registo de aluno')

    def test_encarregado_ve_notas_validadas_do_dependente(self):
        self.client.login(username='encarregado1', password='senha123')
        response = self.client.get(reverse('notas_dependente', args=[self.aluno.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1º Trimestre')
        self.assertNotContains(response, '2º Trimestre')

    def test_encarregado_nao_acede_a_dependente_de_outro(self):
        self.client.login(username='encarregado1', password='senha123')
        response = self.client.get(reverse('notas_dependente', args=[self.outro_aluno.id]))

        self.assertEqual(response.status_code, 403)

    def test_encarregado_lista_dependentes(self):
        self.client.login(username='encarregado1', password='senha123')
        response = self.client.get(reverse('meus_dependentes'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Aluno Teste')
        self.assertNotContains(response, 'Outro Aluno')


class BaseLegalCalculoTestBase(TestCase):
    """Fixtures para testar as fórmulas da "Base Legal EJA"
    (docs/processos_sistema.pdf) — Iº/IIº Ano — direto no ORM, sem HTTP."""

    def setUp(self):
        self.ano_letivo = AnoLetivo.objects.create(descricao='2026')
        self.classe_1ano = Classe.objects.create(nome='Iº')
        self.classe_2ano = Classe.objects.create(nome='IIº')
        self.turma_1ano = Turma.objects.create(nome='A', classe=self.classe_1ano, ano_letivo=self.ano_letivo)
        self.turma_2ano = Turma.objects.create(nome='A', classe=self.classe_2ano, ano_letivo=self.ano_letivo)

        self.matematica = Disciplina.objects.create(nome='Matemática', sigla='MAT', nuclear=True)
        self.portugues = Disciplina.objects.create(nome='Língua Portuguesa', sigla='LP', nuclear=True)
        self.fisica = Disciplina.objects.create(nome='Física', sigla='FIS')
        self.quimica = Disciplina.objects.create(nome='Química', sigla='QUI')
        self.biologia = Disciplina.objects.create(nome='Biologia', sigla='BIO')

        self._contador_aluno = 0

    def _aluno(self, turma):
        self._contador_aluno += 1
        numero = f'NP{self._contador_aluno:04d}'
        encarregado_user = User.objects.create_user(username=f'enc_{numero}', password='senha123')
        encarregado = Encarregado.objects.create(user=encarregado_user, telefone='900000000')
        return Aluno.objects.create(
            nome=f'Aluno {numero}',
            numero_processo=numero,
            data_nascimento=datetime.date(2008, 1, 1),
            sexo='M',
            turma=turma,
            encarregado=encarregado,
        )

    def _resultado(self, aluno, disciplina, **kwargs):
        return ResultadoDisciplina.objects.create(
            aluno=aluno, disciplina=disciplina, ano_letivo=self.ano_letivo, **kwargs
        )


class PrimeiroAnoDisciplinaTests(BaseLegalCalculoTestBase):
    def test_mf_e_media_simples_sem_pesos(self):
        aluno = self._aluno(self.turma_1ano)
        r = self._resultado(aluno, self.fisica, mt1=14, mt2=12, mt3=16)
        self.assertEqual(r.mf, 14)  # (14+12+16)/3 = 14
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_APROVADO)

    def test_disciplina_reprovada_direta_abaixo_de_10(self):
        aluno = self._aluno(self.turma_1ano)
        r = self._resultado(aluno, self.fisica, mt1=4, mt2=5, mt3=6)
        self.assertEqual(r.mf, 5)
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_REPROVADO)

    def test_iano_nao_tem_exame_nem_recurso(self):
        aluno = self._aluno(self.turma_1ano)
        r = self._resultado(aluno, self.fisica, mt1=9, mt2=9, mt3=9, exame=15, nota_recurso=15)
        # Sem exame/recurso no Iº Ano — nota_final fica sempre None, e o
        # resultado só depende da MF.
        self.assertIsNone(r.nota_final)
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_REPROVADO)


class PrimeiroAnoTransicaoAnualTests(BaseLegalCalculoTestBase):
    def test_aprovado_direto_sem_tolerancia(self):
        aluno = self._aluno(self.turma_1ano)
        self._resultado(aluno, self.matematica, mt1=12, mt2=13, mt3=14)
        self._resultado(aluno, self.portugues, mt1=11, mt2=10, mt3=12)
        self._resultado(aluno, self.fisica, mt1=15, mt2=14, mt3=13)

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_APROVADO)

    def test_tolerancia_ate_2_disciplinas_aprova_por_compensacao(self):
        aluno = self._aluno(self.turma_1ano)
        self._resultado(aluno, self.matematica, mt1=12, mt2=13, mt3=14)
        self._resultado(aluno, self.portugues, mt1=11, mt2=10, mt3=12)
        self._resultado(aluno, self.fisica, mt1=8, mt2=9, mt3=8)     # mf=8
        self._resultado(aluno, self.quimica, mt1=9, mt2=8, mt3=9)    # mf=9

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_APROVADO_COMPENSACAO)
        self.assertEqual(
            set(situacao.disciplinas_em_deficiencia.all()),
            {self.fisica, self.quimica},
        )

    def test_mais_de_2_disciplinas_na_tolerancia_reprova(self):
        aluno = self._aluno(self.turma_1ano)
        self._resultado(aluno, self.matematica, mt1=12, mt2=13, mt3=14)
        self._resultado(aluno, self.portugues, mt1=11, mt2=10, mt3=12)
        self._resultado(aluno, self.fisica, mt1=8, mt2=9, mt3=8)
        self._resultado(aluno, self.quimica, mt1=9, mt2=8, mt3=9)
        self._resultado(aluno, self.biologia, mt1=8, mt2=8, mt3=9)

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)

    def test_portugues_e_matematica_simultaneas_na_tolerancia_reprova(self):
        aluno = self._aluno(self.turma_1ano)
        self._resultado(aluno, self.matematica, mt1=8, mt2=9, mt3=8)   # tolerância
        self._resultado(aluno, self.portugues, mt1=9, mt2=8, mt3=9)    # tolerância
        self._resultado(aluno, self.fisica, mt1=15, mt2=14, mt3=13)

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)

    def test_disciplina_abaixo_de_8_reprova_sem_tolerancia(self):
        aluno = self._aluno(self.turma_1ano)
        self._resultado(aluno, self.matematica, mt1=12, mt2=13, mt3=14)
        self._resultado(aluno, self.fisica, mt1=5, mt2=6, mt3=7)  # mf=6

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)


class NotaComExameTests(TestCase):
    def test_calcular_mt_com_exame_pesos_40_60(self):
        # IIº Ano, 3º trimestre: MT = MAC×0,40 + NE×0,60 (NE reaproveita o
        # campo 'npt'). 10×0,40 + 15×0,60 = 4 + 9 = 13.
        nota = Nota(mac=Decimal('10'), npt=Decimal('15'))
        self.assertEqual(nota.calcular_mt_com_exame(), Decimal('13'))


class SegundoAnoDisciplinaTests(BaseLegalCalculoTestBase):
    def test_mfa_e_media_simples_como_no_iano(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=12, mt2=10, mt3=14)
        self.assertEqual(r.mf, 12)  # (12+10+14)/3 = 12
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_APROVADO)

    def test_mfa_igual_ou_abaixo_de_6_reprova_sem_recurso(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=6, mt2=6, mt3=6)
        self.assertEqual(r.mf, 6)
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_REPROVADO)

    def test_mfa_entre_7_e_9_fica_pendente_de_recurso(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)
        self.assertEqual(r.mf, 7)
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_RECURSO)

        r2 = self._resultado(aluno, self.quimica, mt1=8, mt2=9, mt3=8)
        self.assertEqual(r2.resultado, ResultadoDisciplina.RESULTADO_RECURSO)

    def test_nota_recurso_seca_decide_aprovacao(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)  # MFA=7, Recurso
        r.nota_recurso = 12
        r.save()
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_APROVADO)

        r.nota_recurso = 7
        r.save()
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_REPROVADO)


class SegundoAnoTransicaoAnualTests(BaseLegalCalculoTestBase):
    def test_pendente_enquanto_disciplina_aguarda_recurso(self):
        aluno = self._aluno(self.turma_2ano)
        self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)  # MFA=7, sem recurso lançado

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertIsNone(situacao)

    def test_aprovado_direto_sem_recurso(self):
        aluno = self._aluno(self.turma_2ano)
        self._resultado(aluno, self.fisica, mt1=14, mt2=14, mt3=14)
        self._resultado(aluno, self.quimica, mt1=13, mt2=13, mt3=13)

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_APROVADO)

    def test_mfa_igual_ou_abaixo_de_6_reprova_o_aluno_mesmo_sem_recurso(self):
        aluno = self._aluno(self.turma_2ano)
        self._resultado(aluno, self.fisica, mt1=6, mt2=6, mt3=6)  # MFA=6, reprova direto
        self._resultado(aluno, self.quimica, mt1=14, mt2=14, mt3=14)

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)

    def test_recurso_com_sucesso_pleno_aprova_direto(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)
        r.nota_recurso = 12  # >=10 -> deixa de estar na banda de tolerância
        r.save()
        self._resultado(aluno, self.quimica, mt1=14, mt2=14, mt3=14)

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_APROVADO)

    def test_recurso_leva_a_banda_de_tolerancia_aprova_por_compensacao(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)
        r.nota_recurso = 9  # não-nuclear, fica na banda 8-9 -> tolerância anual
        r.save()
        self._resultado(aluno, self.quimica, mt1=14, mt2=14, mt3=14)

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_APROVADO_COMPENSACAO)

    def test_recurso_falhado_reprova(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)
        r.nota_recurso = 5  # continua abaixo de 8 -> reprova, sem segunda hipótese
        r.save()
        self._resultado(aluno, self.quimica, mt1=14, mt2=14, mt3=14)

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)

    def test_ate_2_nao_nucleares_em_8_9_pos_recurso_aprova_por_compensacao(self):
        aluno = self._aluno(self.turma_2ano)
        r1 = self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)
        r1.nota_recurso = 9
        r1.save()
        r2 = self._resultado(aluno, self.quimica, mt1=8, mt2=8, mt3=8)
        r2.nota_recurso = 8
        r2.save()
        self._resultado(aluno, self.biologia, mt1=14, mt2=14, mt3=14)

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_APROVADO_COMPENSACAO)
        self.assertEqual(set(situacao.disciplinas_em_deficiencia.all()), {self.fisica, self.quimica})

    def test_mais_de_2_nao_nucleares_em_8_9_pos_recurso_reprova(self):
        aluno = self._aluno(self.turma_2ano)
        for disciplina in (self.fisica, self.quimica, self.biologia):
            r = self._resultado(aluno, disciplina, mt1=7, mt2=7, mt3=7)
            r.nota_recurso = 9
            r.save()

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)

    def test_nuclear_isolada_em_8_9_pos_recurso_reprova_mesmo_com_outras_positivas(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.matematica, mt1=7, mt2=7, mt3=7)
        r.nota_recurso = 9  # nuclear isolada em 8/9 -> reprova, sem tolerância
        r.save()
        self._resultado(aluno, self.fisica, mt1=14, mt2=14, mt3=14)

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)

    def test_portugues_e_matematica_simultaneas_em_recurso_reprova_de_imediato(self):
        aluno = self._aluno(self.turma_2ano)
        self._resultado(aluno, self.matematica, mt1=8, mt2=9, mt3=8)  # MFA=8, entraria em recurso
        self._resultado(aluno, self.portugues, mt1=9, mt2=8, mt3=9)   # MFA=9, entraria em recurso

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)
        # Veto do gatilho: o recurso fecha-se de imediato para as duas —
        # não fica pendente à espera de NER.
        self.assertEqual(
            ResultadoDisciplina.objects.get(aluno=aluno, disciplina=self.matematica).resultado,
            ResultadoDisciplina.RESULTADO_REPROVADO,
        )
        self.assertEqual(
            ResultadoDisciplina.objects.get(aluno=aluno, disciplina=self.portugues).resultado,
            ResultadoDisciplina.RESULTADO_REPROVADO,
        )

    def test_mais_de_4_disciplinas_em_recurso_reprova_de_imediato(self):
        aluno = self._aluno(self.turma_2ano)
        ingles = Disciplina.objects.create(nome='Inglês', sigla='ING')
        historia = Disciplina.objects.create(nome='História', sigla='HIS')
        for disciplina in (self.fisica, self.quimica, self.biologia, ingles, historia):
            self._resultado(aluno, disciplina, mt1=7, mt2=7, mt3=7)  # 5 disciplinas em recurso

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)
        self.assertEqual(
            ResultadoDisciplina.objects.filter(
                aluno=aluno, resultado=ResultadoDisciplina.RESULTADO_RECURSO
            ).count(),
            0,
        )

    def test_disciplina_reprovada_direto_fecha_recurso_nas_outras(self):
        # Caso reportado: aluna com uma disciplina em 6 (reprova sem
        # recurso) não pode ir a recurso a mais nada — mesmo tendo outras
        # disciplinas na banda 7-9.
        aluno = self._aluno(self.turma_2ano)
        self._resultado(aluno, self.fisica, mt1=6, mt2=6, mt3=6)      # MFA=6, reprova directo
        self._resultado(aluno, self.quimica, mt1=9, mt2=9, mt3=9)     # MFA=9, entraria em recurso

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)
        self.assertEqual(
            ResultadoDisciplina.objects.get(aluno=aluno, disciplina=self.quimica).resultado,
            ResultadoDisciplina.RESULTADO_REPROVADO,
        )

    def test_disciplina_reprovada_direto_reverte_recurso_ja_lancado(self):
        # Caso Isabela Barbosa: a NER já tinha sido lançada (e aprovada)
        # numa disciplina que nunca devia ter tido essa hipótese, porque
        # outra disciplina do mesmo aluno reprovou directamente (MFA<=6).
        # O recálculo tem de reverter isso para Reprovado.
        aluno = self._aluno(self.turma_2ano)
        self._resultado(aluno, self.fisica, mt1=6, mt2=6, mt3=6)  # MFA=6, reprova directo
        r = self._resultado(aluno, self.quimica, mt1=9, mt2=9, mt3=9)  # MFA=9
        r.nota_recurso = 12  # recurso indevidamente lançado e "aprovado" antes da correcção
        r.save()
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_APROVADO)  # estado antes do fix

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)
        r.refresh_from_db()
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_REPROVADO)

    def test_faltas_numa_disciplina_fecha_recurso_nas_outras(self):
        professor_user = User.objects.create_user(username='prof_faltas_ii', password='senha123')
        professor = Professor.objects.create(user=professor_user, numero_funcionario='PF2ANO')
        atribuicao = AtribuicaoDocente.objects.create(
            professor=professor, disciplina=self.fisica,
            turma=self.turma_2ano, ano_letivo=self.ano_letivo,
        )
        HorarioAula.objects.create(
            turma=self.turma_2ano, dia_semana=HorarioAula.SEGUNDA, tempo=1, atribuicao=atribuicao
        )
        PeriodoAcademico.objects.create(
            nome='1º Trimestre', ano_letivo=self.ano_letivo, aberto=True,
            data_inicio_lancamento=datetime.date(2026, 2, 1),
            data_fim_lancamento=datetime.date(2026, 4, 30),
        )
        aluno = self._aluno(self.turma_2ano)
        for semana in range(3):  # excede o limite de 3 faltas/trimestre
            Frequencia.objects.create(
                aluno=aluno, atribuicao=atribuicao,
                data=datetime.date(2026, 2, 3) + datetime.timedelta(days=semana * 7),
                estado=Frequencia.FALTA,
            )

        self._resultado(aluno, self.fisica, mt1=18, mt2=18, mt3=18)   # reprova por faltas
        self._resultado(aluno, self.quimica, mt1=9, mt2=9, mt3=9)     # entraria em recurso

        situacao = verificar_transicao_aluno(aluno, self.ano_letivo)
        self.assertEqual(situacao.situacao, SituacaoAnual.SITUACAO_REPROVADO)
        self.assertEqual(
            ResultadoDisciplina.objects.get(aluno=aluno, disciplina=self.quimica).resultado,
            ResultadoDisciplina.RESULTADO_REPROVADO,
        )


class FaltasReprovamDisciplinaTests(BaseLegalCalculoTestBase):
    def test_excede_limite_de_faltas_reprova_disciplina_mesmo_com_boas_notas(self):
        professor_user = User.objects.create_user(username='prof_faltas', password='senha123')
        professor = Professor.objects.create(user=professor_user, numero_funcionario='PF001')
        atribuicao = AtribuicaoDocente.objects.create(
            professor=professor, disciplina=self.fisica,
            turma=self.turma_1ano, ano_letivo=self.ano_letivo,
        )
        # 1 tempo lectivo semanal -> limite de 3 faltas/trimestre.
        HorarioAula.objects.create(
            turma=self.turma_1ano, dia_semana=HorarioAula.SEGUNDA, tempo=1, atribuicao=atribuicao
        )
        PeriodoAcademico.objects.create(
            nome='1º Trimestre', ano_letivo=self.ano_letivo, aberto=True,
            data_inicio_lancamento=datetime.date(2026, 2, 1),
            data_fim_lancamento=datetime.date(2026, 4, 30),
        )

        aluno = self._aluno(self.turma_1ano)
        for semana in range(3):
            Frequencia.objects.create(
                aluno=aluno, atribuicao=atribuicao,
                data=datetime.date(2026, 2, 3) + datetime.timedelta(days=semana * 7),
                estado=Frequencia.FALTA,
            )

        r = self._resultado(aluno, self.fisica, mt1=18, mt2=18, mt3=18)
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_REPROVADO_FALTAS)

    def test_abaixo_do_limite_de_faltas_nao_afeta_resultado(self):
        professor_user = User.objects.create_user(username='prof_faltas2', password='senha123')
        professor = Professor.objects.create(user=professor_user, numero_funcionario='PF002')
        atribuicao = AtribuicaoDocente.objects.create(
            professor=professor, disciplina=self.fisica,
            turma=self.turma_1ano, ano_letivo=self.ano_letivo,
        )
        HorarioAula.objects.create(
            turma=self.turma_1ano, dia_semana=HorarioAula.SEGUNDA, tempo=1, atribuicao=atribuicao
        )
        PeriodoAcademico.objects.create(
            nome='1º Trimestre', ano_letivo=self.ano_letivo, aberto=True,
            data_inicio_lancamento=datetime.date(2026, 2, 1),
            data_fim_lancamento=datetime.date(2026, 4, 30),
        )

        aluno = self._aluno(self.turma_1ano)
        for semana in range(2):  # abaixo do limite de 3
            Frequencia.objects.create(
                aluno=aluno, atribuicao=atribuicao,
                data=datetime.date(2026, 2, 3) + datetime.timedelta(days=semana * 7),
                estado=Frequencia.FALTA,
            )

        r = self._resultado(aluno, self.fisica, mt1=18, mt2=18, mt3=18)
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_APROVADO)


class PautaGeralObservacaoTests(BaseLegalCalculoTestBase):
    """A coluna "Observação" da pauta geral: lista as disciplinas ainda
    pendentes de recurso, ou um simples "Recurso" depois de resolvido — o
    resultado (Aprovado/Reprovado) já vai na coluna "Situação Geral", não é
    repetido aqui — ver services/resultados.py:_info_recurso."""

    def setUp(self):
        super().setUp()
        professor_user = User.objects.create_user(username='prof_obs', password='senha123')
        professor = Professor.objects.create(user=professor_user, numero_funcionario='POBS1')
        for turma in (self.turma_1ano, self.turma_2ano):
            for disciplina in (self.fisica, self.quimica):
                AtribuicaoDocente.objects.create(
                    professor=professor, disciplina=disciplina, turma=turma, ano_letivo=self.ano_letivo,
                )

    def _observacao_do_aluno(self, turma, aluno):
        _, linhas = montar_pauta_final_turma(turma, self.ano_letivo)
        linha = next(l for l in linhas if l['aluno'] == aluno)
        return linha['observacao']

    def test_lista_disciplinas_pendentes_de_recurso(self):
        aluno = self._aluno(self.turma_2ano)
        self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)      # MFA=7, Recurso
        self._resultado(aluno, self.quimica, mt1=14, mt2=14, mt3=14)  # Aprovado

        self.assertEqual(self._observacao_do_aluno(self.turma_2ano, aluno), 'Recurso: Física')

    def test_aprovado_apos_recurso_reduz_a_recurso(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)
        r.nota_recurso = 12
        r.save()
        self._resultado(aluno, self.quimica, mt1=14, mt2=14, mt3=14)

        self.assertEqual(self._observacao_do_aluno(self.turma_2ano, aluno), 'Recurso')

    def test_reprovado_apos_recurso_reduz_a_recurso(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)
        r.nota_recurso = 5
        r.save()
        self._resultado(aluno, self.quimica, mt1=14, mt2=14, mt3=14)

        self.assertEqual(self._observacao_do_aluno(self.turma_2ano, aluno), 'Recurso')

    def test_aprovado_directo_fica_em_branco_mesmo_com_outro_aluno_em_recurso(self):
        aluno_directo = self._aluno(self.turma_2ano)
        self._resultado(aluno_directo, self.fisica, mt1=14, mt2=14, mt3=14)
        self._resultado(aluno_directo, self.quimica, mt1=12, mt2=12, mt3=12)

        self.assertEqual(self._observacao_do_aluno(self.turma_2ano, aluno_directo), '')

    def test_reprovado_directo_sem_recurso_fica_em_branco(self):
        aluno = self._aluno(self.turma_2ano)
        self._resultado(aluno, self.fisica, mt1=5, mt2=5, mt3=5)  # MFA<=6, reprova sem recurso
        self._resultado(aluno, self.quimica, mt1=14, mt2=14, mt3=14)

        self.assertEqual(self._observacao_do_aluno(self.turma_2ano, aluno), '')

    def test_vazia_quando_nunca_houve_recurso(self):
        aluno = self._aluno(self.turma_1ano)
        self._resultado(aluno, self.fisica, mt1=14, mt2=14, mt3=14)

        self.assertEqual(self._observacao_do_aluno(self.turma_1ano, aluno), '')

    def test_pagina_pauta_final_mostra_botao_de_detalhe_apos_recurso_resolvido(self):
        grupo_admin, _ = Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        admin_user = User.objects.create_user(username='admin_obs', password='senha123')
        admin_user.groups.add(grupo_admin)

        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)
        r.nota_recurso = 12
        r.save()
        self._resultado(aluno, self.quimica, mt1=14, mt2=14, mt3=14)

        self.client.login(username='admin_obs', password='senha123')
        response = self.client.get(
            reverse('pauta_final_turma'),
            {'turma': self.turma_2ano.id, 'ano_letivo': self.ano_letivo.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'recurso-detalhe-btn')
        self.assertContains(response, 'id="modalRecursoDetalhe"')
        self.assertContains(response, '"resultado": "Aprovado"')

    def test_pagina_pauta_final_sem_botao_enquanto_recurso_pendente(self):
        grupo_admin, _ = Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        admin_user = User.objects.create_user(username='admin_obs2', password='senha123')
        admin_user.groups.add(grupo_admin)

        aluno = self._aluno(self.turma_2ano)
        self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)  # Recurso, sem NER ainda

        self.client.login(username='admin_obs2', password='senha123')
        response = self.client.get(
            reverse('pauta_final_turma'),
            {'turma': self.turma_2ano.id, 'ano_letivo': self.ano_letivo.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'recurso-detalhe-btn')
        self.assertContains(response, 'Recurso: Física')


class MiniPautaRecursoTests(BaseLegalCalculoTestBase):
    """A mini-pauta do IIIº trimestre passa a permitir o lançamento da NER
    directamente ali — só ao professor titular da disciplina ou ao admin
    (ver _pode_editar_mini_pauta em pautas/views.py)."""

    def setUp(self):
        super().setUp()
        grupo_admin, _ = Group.objects.get_or_create(name='Sub-diretor Pedagógico')
        grupo_professor, _ = Group.objects.get_or_create(name='Professor')

        self.admin_user = User.objects.create_user(username='admin_mp', password='senha123')
        self.admin_user.groups.add(grupo_admin)

        self.professor_user = User.objects.create_user(username='prof_mp', password='senha123')
        self.professor_user.groups.add(grupo_professor)
        professor = Professor.objects.create(user=self.professor_user, numero_funcionario='PMP1')
        AtribuicaoDocente.objects.create(
            professor=professor, disciplina=self.fisica, turma=self.turma_2ano, ano_letivo=self.ano_letivo,
        )

        self.outro_professor_user = User.objects.create_user(username='outro_prof_mp', password='senha123')
        self.outro_professor_user.groups.add(grupo_professor)
        Professor.objects.create(user=self.outro_professor_user, numero_funcionario='PMP2')

        self.aluno = self._aluno(self.turma_2ano)
        self.resultado = self._resultado(self.aluno, self.fisica, mt1=7, mt2=7, mt3=7)  # Recurso

    def _url(self):
        return (
            reverse('mini_pauta_trimestral')
            + f'?turma={self.turma_2ano.id}&disciplina={self.fisica.id}&ano_letivo={self.ano_letivo.id}'
        )

    def test_professor_titular_grava_ner(self):
        self.client.login(username='prof_mp', password='senha123')
        response = self.client.post(self._url(), {f'ner_{self.aluno.id}': '12'})

        self.resultado.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.resultado.resultado, ResultadoDisciplina.RESULTADO_APROVADO)

    def test_admin_tambem_pode_gravar(self):
        self.client.login(username='admin_mp', password='senha123')
        response = self.client.post(self._url(), {f'ner_{self.aluno.id}': '9'})

        self.resultado.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.resultado.nota_recurso, Decimal('9.0'))

    def test_professor_sem_atribuicao_nao_pode_gravar(self):
        self.client.login(username='outro_prof_mp', password='senha123')
        response = self.client.post(self._url(), {f'ner_{self.aluno.id}': '12'})

        self.resultado.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(self.resultado.nota_recurso)

    def test_gravar_ner_reabre_resultado_ja_validado(self):
        self.resultado.marcar_validada(self.admin_user)
        self.assertEqual(self.resultado.status, ResultadoDisciplina.STATUS_VALIDADA)

        self.client.login(username='prof_mp', password='senha123')
        self.client.post(self._url(), {f'ner_{self.aluno.id}': '12'})

        self.resultado.refresh_from_db()
        self.assertEqual(self.resultado.status, ResultadoDisciplina.STATUS_RASCUNHO)
        self.assertIsNone(self.resultado.validado_por)
        self.assertIsNone(self.resultado.validado_em)

    def test_gravar_ner_nao_mexe_em_resultado_ja_rascunho(self):
        self.assertEqual(self.resultado.status, ResultadoDisciplina.STATUS_RASCUNHO)

        self.client.login(username='prof_mp', password='senha123')
        self.client.post(self._url(), {f'ner_{self.aluno.id}': '12'})

        self.resultado.refresh_from_db()
        self.assertEqual(self.resultado.status, ResultadoDisciplina.STATUS_RASCUNHO)


class LancamentoNotasColunaMfaTests(BaseLegalCalculoTestBase):
    """A coluna MFA em Lançamento de Notas (3º trimestre, IIº Ano) mostra a
    média anual que decide Aprovado/Recurso/Reprovado — evita confundir com
    o MT (só deste trimestre). Ver static/js/lancamento_notas.js."""

    def setUp(self):
        super().setUp()
        grupo_professor, _ = Group.objects.get_or_create(name='Professor')
        professor_user = User.objects.create_user(username='prof_mfa', password='senha123')
        professor_user.groups.add(grupo_professor)
        professor = Professor.objects.create(user=professor_user, numero_funcionario='PMFA1')
        self.atribuicao = AtribuicaoDocente.objects.create(
            professor=professor, disciplina=self.fisica, turma=self.turma_2ano, ano_letivo=self.ano_letivo,
        )
        self.periodo3 = PeriodoAcademico.objects.create(
            nome='3º Trimestre', ano_letivo=self.ano_letivo, aberto=True,
        )
        self.client.login(username='prof_mfa', password='senha123')

    def test_coluna_mfa_aparece_no_iiiano_terceiro_trimestre(self):
        response = self.client.get(
            reverse('lancamento_notas') + f'?atribuicao={self.atribuicao.id}&periodo={self.periodo3.id}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'MFA')

    def test_coluna_mfa_nao_aparece_no_primeiro_trimestre(self):
        periodo1 = PeriodoAcademico.objects.create(
            nome='1º Trimestre', ano_letivo=self.ano_letivo, aberto=True,
        )
        response = self.client.get(
            reverse('lancamento_notas') + f'?atribuicao={self.atribuicao.id}&periodo={periodo1.id}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'MFA')


class RecalcularResultadosCommandTests(BaseLegalCalculoTestBase):
    """O comando 'recalcular_resultados' existe para corrigir ResultadoDisciplina
    gravados com uma fórmula antiga, sem apagar/recriar nada (ao contrário de
    gerar_resultados_finais) — ver pautas/management/commands/recalcular_resultados.py."""

    def test_recalcula_resultado_desatualizado_sem_perder_nota_recurso(self):
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=8, mt2=8, mt3=8)
        r.nota_recurso = Decimal('12')
        r.save()
        # Simula um registo gravado com uma fórmula antiga: "resultado"
        # desatualizado directamente na BD, sem passar por save() — os
        # restantes campos (nota_recurso incluído) ficam como estavam.
        ResultadoDisciplina.objects.filter(pk=r.pk).update(resultado='Reprovado')

        saida = StringIO()
        call_command('recalcular_resultados', stdout=saida)

        r.refresh_from_db()
        self.assertEqual(r.resultado, ResultadoDisciplina.RESULTADO_APROVADO)
        self.assertEqual(r.nota_recurso, Decimal('12.0'))
        self.assertIn('1 resultado(s) recalculado(s), 1 com classificação alterada.', saida.getvalue())

    def test_filtra_por_ano_letivo(self):
        outro_ano = AnoLetivo.objects.create(descricao='2027')
        aluno = self._aluno(self.turma_2ano)
        r = self._resultado(aluno, self.fisica, mt1=7, mt2=7, mt3=7)
        ResultadoDisciplina.objects.filter(pk=r.pk).update(resultado='Reprovado')

        saida = StringIO()
        call_command('recalcular_resultados', '--ano-letivo', outro_ano.id, stdout=saida)

        r.refresh_from_db()
        self.assertEqual(r.resultado, 'Reprovado')  # fora do ano filtrado, não mexe
        self.assertIn('0 resultado(s) recalculado(s)', saida.getvalue())
