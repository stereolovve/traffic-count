def reset_app(self):
    """Reseta o estado da aplicação e mostra a tela de login"""
    self.tokens = None
    self.username = None
    self.user_preferences = {}
    
    # Limpar a página atual
    if self.page:
        self.page.controls.clear()
        # Mostrar a tela de login
        self.page.add(LoginPage(self))
        self.page.update() 