from .views import can_edit

def can_edit_processor(request):
    """
    Adiciona a flag can_edit ao contexto de templates.
    """
    return {'can_edit': can_edit(request.user) if request.user.is_authenticated else False}
