# Manual de Utilização — Sistema de Gestão de Pautas

Complexo Escolar N.º 2032 - General Ngueto

Este manual explica como usar o sistema no dia a dia, organizado por **perfil de
utilizador**. Cada perfil vê um menu e um painel diferentes, de acordo com o
grupo a que pertence a sua conta.

## Capítulos

1. [Acesso ao sistema](#acesso-ao-sistema) (esta página)
2. [Manual do Administrador](01_administrador.md)
3. [Manual do Professor](02_professor.md)
4. [Manual do Aluno](03_aluno.md)
5. [Manual do Encarregado](04_encarregado.md)
6. [Perguntas frequentes](#perguntas-frequentes)

---

## Acesso ao sistema

### Entrar (login)

1. Na página inicial, clique no botão **Entrar** (canto superior direito do
   cabeçalho).
2. Introduza o seu **utilizador** e **password**.
3. Após entrar, é encaminhado automaticamente para o seu **Painel** — o
   sistema reconhece o seu perfil (Administrador, Professor, Aluno ou
   Encarregado) e mostra o painel e o menu correspondentes.

Não existe recuperação automática de password ("esqueci-me da password") no
site. Se perder a password, peça ao **Administrador** para lha redefinir
(painel de administração do Django).

### Quem tem conta de acesso

| Perfil | Tem login? | Como é criada |
|---|---|---|
| Administrador | Sim | Superutilizador Django, ou conta colocada no grupo "Administrador" |
| Professor | Sim | Criada pelo Administrador em **Cadastros → Professores → Novo Professor** (já inclui o utilizador de acesso) |
| Encarregado | Sim | Criada pelo Administrador (ver [Manual do Administrador](01_administrador.md#criar-um-encarregado)) |
| Aluno | Opcional | Criada pelo Administrador via Django Admin e depois associada à ficha do aluno (ver [Manual do Administrador](01_administrador.md#dar-acesso-a-um-aluno)) — um aluno **sem** conta associada não consegue entrar no sistema |

### Alterar os seus dados e a password

Todos os perfis podem, a qualquer momento, ir a **Perfil** (normalmente no
canto superior direito, junto ao nome do utilizador) para:

- Atualizar nome, apelido e email;
- Alterar a password (é preciso indicar a password atual).

### Notificações

O ícone de sino no topo mostra as **notificações** do sistema — por exemplo,
quando uma pauta é devolvida com erro, quando um pedido de documento é
autorizado/recusado, ou quando um pagamento é confirmado. Está disponível a
todos os perfis autenticados.

---

## Perguntas frequentes

**Entrei no sistema mas não vejo nada / vejo "sem permissão".**
A sua conta não está associada a nenhum grupo (Administrador/Professor/
Aluno/Encarregado). Contacte o Administrador para verificar o seu perfil.

**Sou aluno e não consigo ver as minhas notas.**
As notas só ficam visíveis depois de o Administrador **validar** a pauta do
trimestre. Antes disso (pauta em rascunho ou devolvida "com erros" ao
professor), o aluno e o encarregado não veem nada dessa disciplina/período.

**Sou professor e não consigo lançar notas.**
O lançamento só é permitido dentro do **período de lançamento aberto**
(configurado pelo Administrador em Cadastros → Períodos Académicos). Fora
desse prazo, o formulário fica bloqueado.

**Esqueci-me da password.**
Não há recuperação automática — peça ao Administrador para lhe definir uma
nova password.

**Como peço um Boletim ou Certificado?**
Só o **próprio Aluno** pode solicitar (não o Encarregado) — ver
[Manual do Aluno](03_aluno.md#solicitar-boletim-ou-certificado).
