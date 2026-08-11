from .models import Escola


def escola_config(request):
    return {'escola': Escola.obter_configuracao()}
