from django.urls import reverse_lazy
from django.views.generic import (ListView, CreateView,
    UpdateView, DeleteView)
from .models import Frequencia
from .forms import FrequenciaForm

class FrequenciaListView(ListView):
    model = Frequencia
    template_name = 'frequencias/lista.html'
    context_object_name = 'frequencias'
    paginate_by = 20

class FrequenciaCreateView(CreateView):
    model = Frequencia
    form_class = FrequenciaForm
    template_name = 'frequencias/form.html'
    success_url = reverse_lazy('frequencia_lista' )

class FrequenciaUpdateView(UpdateView):
    model = Frequencia
    form_class = FrequenciaForm
    template_name = 'frequencias/form.html'
    success_url = reverse_lazy('frequencia_lista' )

class FrequenciaDeleteView(DeleteView):
    model = Frequencia
    template_name = 'frequencias/excluir.html'
    success_url = reverse_lazy('frequencia_lista' )