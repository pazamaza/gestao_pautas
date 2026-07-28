import datetime
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from alunos.models import Aluno, Encarregado
from disciplinas.models import Disciplina
from frequencias.models import Frequencia
from notificacoes.models import Notificacao
from professores.models import AtribuicaoDocente, DiretorTurma, Professor
from turmas.models import AnoLetivo, Classe, HorarioAula, PeriodoAcademico, Turma

from .models import Avaliacao, Nota, ResultadoDisciplina, SituacaoAnual
from .services.resultados import verificar_transicao_aluno


class PautasTestBase(TestCase):
    def setUp(self):
        self.grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
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
