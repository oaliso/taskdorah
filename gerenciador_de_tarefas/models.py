from extensions import db
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import or_, and_

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    nomeUsuario = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    tarefasCriadas = db.relationship('Tarefa', backref='criador', foreign_keys='Tarefa.criador_id', lazy=True)
    tarefasAtribuidas = db.relationship('Tarefa', backref='responsavel', foreign_keys='Tarefa.responsavel_id', lazy=True)
    cargo = db.Column(db.String(20), nullable=False, default='usuario') 
    def contatoCom(self, amigo):
        return Contato.query.filter(                                              # ! Retorna o registro de Contato entre os dois (em qualquer direção), ou None.
            or_(
                and_(Contato.solicitante_id == self.id, Contato.destinatario_id == amigo.id),
                and_(Contato.solicitante_id == amigo.id, Contato.destinatario_id == self.id),
            )
        ).first()

    def saoContatos(self, amigo):
        c = self.contatoCom(amigo)
        return c is not None and c.status == 'aceito'

    def podeAtribuirA(self, amigo):
        return amigo.id == self.id or self.saoContatos(amigo)                     # ! permite atribuir a atividade a si mesmo ou a um amigo

    @property
    def contatos(self): # Lista de amigos.
        aceitos = Contato.query.filter(
            Contato.status == 'aceito',
            or_(Contato.solicitante_id == self.id, Contato.destinatario_id == self.id)
        ).all()
        ids = [c.destinatario_id if c.solicitante_id == self.id else c.solicitante_id
               for c in aceitos]
        return Usuario.query.filter(Usuario.id.in_(ids)).all() if ids else []

class Tarefa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pendente')
    prioridade = db.Column(db.String(20), nullable=False, default='A definir')
    prazo = db.Column(db.DateTime, nullable=True, index=True)
    criador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    responsavel_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

class Contato(db.Model):
    __tablename__ = 'contato'

    id = db.Column(db.Integer, primary_key=True)
    solicitante_id = db.Column(db.Integer, db.ForeignKey('usuario.id', ondelete='CASCADE'),
                               nullable=False, index=True)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', ondelete='CASCADE'),
                                nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='pendente')         # ! status de  pendente, aceito, recusado
    criadoEm = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    respondidoEm = db.Column(db.DateTime, nullable=True)
    solicitante = db.relationship('Usuario', foreign_keys=[solicitante_id],
                                  backref=db.backref('solicitacoesEnviadas', lazy=True,
                                                     cascade='all, delete-orphan'))
    destinatario = db.relationship('Usuario', foreign_keys=[destinatario_id],
                                   backref=db.backref('solicitacoesRecebidas', lazy=True,
                                                      cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('solicitante_id', 'destinatario_id', name='uq_contato_par'),
        db.CheckConstraint('solicitante_id <> destinatario_id', name='ck_contato_nao_si_mesmo'),
    )