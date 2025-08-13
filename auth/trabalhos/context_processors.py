from .views import can_edit, is_contagem_user

def can_edit_processor(request):
    """
    Adiciona as flags can_edit e is_contagem_user ao contexto de templates.
    """
    return {
        'can_edit': can_edit(request.user) if request.user.is_authenticated else False,
        'is_contagem_user': is_contagem_user(request.user) if request.user.is_authenticated else False
    }
