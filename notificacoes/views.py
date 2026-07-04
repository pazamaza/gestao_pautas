from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Notificacao


@login_required
def notificacao_lista(request):
    notificacoes = Notificacao.objects.filter(destinatario=request.user)
    return render(request, 'notificacoes/lista.html', {'notificacoes': notificacoes})


@login_required
def notificacao_marcar_lida(request, pk):
    notificacao = get_object_or_404(Notificacao, pk=pk, destinatario=request.user)

    if request.method == 'POST':
        notificacao.lida = True
        notificacao.save()

    return redirect('notificacao_lista')
