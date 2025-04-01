class Historico(Base):
    __tablename__ = 'historico'
    
    id = Column(Integer, primary_key=True)
    sessao = Column(String)
    categoria_id = Column(Integer, ForeignKey('categoria.id'))
    movimento = Column(String)
    acao = Column(String)  # increment, decrement, reset, salvamento, observacao, etc
    observacao = Column(String, nullable=True)  # Para armazenar observações ou detalhes adicionais
    timestamp = Column(DateTime, default=datetime.now)
    
    categoria = relationship("Categoria") 