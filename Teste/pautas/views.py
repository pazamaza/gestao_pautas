from django.views.generic import ListView
from django.shortcuts import render
from alunos.models import Aluno
from turmas.models import Turma
from .models import Nota
from django.forms import modelformset_factory
from .models import Nota

class NotaListView(ListView):
    model = Nota
    template_name = 'pautas/lista_notas.html'
    context_object_name = 'notas'

def pauta_turma(request, turma_id):

    turma = Turma.objects.get(
        id=turma_id
    )

    alunos = Aluno.objects.filter(
        turma=turma
    ).order_by('nome')

    context = {

        'turma': turma,
        'alunos': alunos,

    }

    return render(
        request,
        'pautas/pauta_turma.html',
        context
    )

def pauta_lancamento(request):

    NotaFormSet = modelformset_factory(
        Nota,
        fields=('mac', 'npp', 'npt'),
        extra=0
    )

    queryset = Nota.objects.all()

    if request.method == 'POST':

        formset = NotaFormSet(
            request.POST,
            queryset=queryset
        )

        if formset.is_valid():

            formset.save()

    else:

        formset = NotaFormSet(
            queryset=queryset
        )

    return render(
        request,
        'pautas/lancamento.html',
        {
            'formset': formset
        }
    )