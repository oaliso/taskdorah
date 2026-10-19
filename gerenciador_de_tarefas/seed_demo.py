from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from app import STATUS_ENCERRADOS, STATUS_VALIDOS, app
from extensions import db
from models import Contato, Tarefa, Usuario


SENHA_DEMO = 'demo123'

USUARIOS_DEMO = (
    {
        'nomeUsuario': 'admin_demo',
        'nome': 'Administrador Demo',
        'email': 'admin@taskdorah.demo',
        'cargo': 'admin',
    },
    {
        'nomeUsuario': 'ana_demo',
        'nome': 'Ana Demo',
        'email': 'ana@taskdorah.demo',
        'cargo': 'usuario',
    },
    {
        'nomeUsuario': 'bruno_demo',
        'nome': 'Bruno Demo',
        'email': 'bruno@taskdorah.demo',
        'cargo': 'usuario',
    },
)


def obter_ou_criar_usuario(dados):
    usuario = Usuario.query.filter(
        (Usuario.email == dados['email'])
        | (Usuario.nomeUsuario == dados['nomeUsuario'])
    ).first()

    if usuario is None:
        usuario = Usuario(
            nomeUsuario=dados['nomeUsuario'],
            nome=dados['nome'],
            email=dados['email'],
            senha=generate_password_hash(SENHA_DEMO),
            cargo=dados['cargo'],
        )
        db.session.add(usuario)
    else:
        usuario.nomeUsuario = dados['nomeUsuario']
        usuario.nome = dados['nome']
        usuario.email = dados['email']
        usuario.senha = generate_password_hash(SENHA_DEMO)
        usuario.cargo = dados['cargo']

    return usuario


def criar_tarefa(titulo, descricao, status, prioridade, prazo, criador, responsavel):
    return Tarefa(
        titulo=titulo,
        descricao=descricao,
        status=status,
        prioridade=prioridade,
        prazo=prazo,
        criador_id=criador.id,
        responsavel_id=responsavel.id,
    )


def popular_demo():
    agora = datetime.now()
    usuarios = {
        dados['nomeUsuario']: obter_ou_criar_usuario(dados)
        for dados in USUARIOS_DEMO
    }
    db.session.flush()

    ids_demo = [usuario.id for usuario in usuarios.values()]

    Tarefa.query.filter(Tarefa.criador_id.in_(ids_demo)).delete(
        synchronize_session=False
    )
    Contato.query.filter(
        Contato.solicitante_id.in_(ids_demo),
        Contato.destinatario_id.in_(ids_demo),
    ).delete(synchronize_session=False)

    admin = usuarios['admin_demo']
    ana = usuarios['ana_demo']
    bruno = usuarios['bruno_demo']

    contatos = (
        Contato(
            solicitante_id=admin.id,
            destinatario_id=ana.id,
            status='aceito',
            respondidoEm=agora,
        ),
        Contato(
            solicitante_id=admin.id,
            destinatario_id=bruno.id,
            status='aceito',
            respondidoEm=agora,
        ),
        Contato(
            solicitante_id=ana.id,
            destinatario_id=bruno.id,
            status='aceito',
            respondidoEm=agora,
        ),
    )

    criadores = (admin, ana, bruno)
    responsaveis = (ana, bruno, admin)
    prioridades = ('Alta', 'Média', 'Baixa', 'A definir')
    tarefas = []

    for indice, status in enumerate(STATUS_VALIDOS):
        prazo = agora + timedelta(days=indice + 1)
        if status in STATUS_ENCERRADOS:
            prazo = agora - timedelta(days=indice + 1)

        tarefas.append(
            criar_tarefa(
                f'Tarefa {status}',
                f'Exemplo de tarefa com o status {status}.',
                status,
                prioridades[indice % len(prioridades)],
                prazo,
                criadores[indice % len(criadores)],
                responsaveis[indice % len(responsaveis)],
            )
        )

    status_aberto = next(
        status for status in STATUS_VALIDOS if status not in STATUS_ENCERRADOS
    )
    tarefas.append(
        criar_tarefa(
            'Entregar relatório atrasado',
            'Exemplo de tarefa com prazo vencido e status ainda aberto.',
            status_aberto,
            'Alta',
            agora - timedelta(days=2),
            ana,
            admin,
        )
    )

    db.session.add_all(contatos)
    db.session.add_all(tarefas)
    db.session.commit()

    print('Dados de demonstração criados com sucesso.')
    print('Usuários: admin_demo, ana_demo e bruno_demo')
    print(f'Senha de todos os usuários: {SENHA_DEMO}')
    print(
        f'Foram criados {len(contatos)} contatos aceitos e {len(tarefas)} tarefas, '
        'incluindo 1 atrasada.'
    )


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        popular_demo()
