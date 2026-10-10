import os
import secrets
import sqlite3
from datetime import date
from functools import wraps
from pathlib import Path

import click
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

STATUS = {"pendente": "Pendente", "andamento": "Em andamento", "concluida": "Concluída", "cancelada": "Cancelada"}
PRIORIDADES = {"baixa": "Baixa", "media": "Média", "alta": "Alta"}


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret_file = Path(app.instance_path) / 'secret.key'
    if not secret_file.exists():
        try:
            with secret_file.open('x') as handle:
                handle.write(secrets.token_hex(32))
            secret_file.chmod(0o600)
        except FileExistsError:
            pass
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secret_file.read_text(),
                      DATABASE=str(Path(app.instance_path) / 'taskdorah.db'),
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
    if config:
        app.config.update(config)

    def db():
        if 'db' not in g:
            g.db = sqlite3.connect(app.config['DATABASE'])
            g.db.row_factory = sqlite3.Row
            g.db.execute('PRAGMA foreign_keys = ON')
        return g.db

    @app.teardown_appcontext
    def close_db(error=None):
        connection = g.pop('db', None)
        if connection:
            connection.close()

    with app.app_context():
        db().executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL, admin INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS contatos (
                id INTEGER PRIMARY KEY, nome TEXT NOT NULL, email TEXT NOT NULL DEFAULT '',
                telefone TEXT NOT NULL DEFAULT '', usuario_id INTEGER NOT NULL REFERENCES usuarios(id));
            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, descricao TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pendente', prioridade TEXT NOT NULL DEFAULT 'media',
                prazo TEXT NOT NULL DEFAULT '', usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                contato_id INTEGER REFERENCES contatos(id) ON DELETE SET NULL);
        """)

    @app.cli.command('criar-usuario')
    @click.argument('nome')
    @click.option('--admin', is_flag=True, help='Concede acesso ao painel administrativo.')
    @click.password_option(confirmation_prompt=True)
    def criar_usuario(nome, admin, password):
        if not nome.strip() or len(password) < 8:
            raise click.ClickException('Informe um nome e uma senha com pelo menos 8 caracteres.')
        try:
            db().execute('INSERT INTO usuarios (nome, senha, admin) VALUES (?, ?, ?)',
                         (nome.strip(), generate_password_hash(password), int(admin)))
            db().commit()
        except sqlite3.IntegrityError:
            raise click.ClickException('Esse usuário já existe.')
        click.echo('Usuário criado.')

    @app.before_request
    def load_user():
        g.user = db().execute('SELECT * FROM usuarios WHERE id = ?', (session.get('user_id'),)).fetchone()
        session.setdefault('csrf', secrets.token_hex(32))
        if request.method == 'POST':
            if not secrets.compare_digest(session['csrf'], request.form.get('csrf', '')):
                abort(400, 'Formulário expirado. Recarregue a página e tente novamente.')

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                return redirect(url_for('login'))
            return view(*args, **kwargs)
        return wrapped

    @app.context_processor
    def common():
        return dict(status_opcoes=STATUS, prioridades=PRIORIDADES, hoje=date.today().isoformat())

    def owned(table, item_id):
        # table is only supplied by the route implementations below.
        item = db().execute(f'SELECT * FROM {table} WHERE id = ?', (item_id,)).fetchone()
        if item is None:
            abort(404)
        if not g.user['admin'] and item['usuario_id'] != g.user['id']:
            abort(403)
        return item

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            user = db().execute('SELECT * FROM usuarios WHERE nome = ?', (request.form.get('nome', '').strip(),)).fetchone()
            if user and check_password_hash(user['senha'], request.form.get('senha', '')):
                session.clear()
                session['user_id'] = user['id']
                session['csrf'] = secrets.token_hex(32)
                return redirect(url_for('quadro'))
            flash('Usuário ou senha inválidos.', 'erro')
        return render_template('login.html')

    @app.post('/sair')
    def sair():
        session.clear()
        return redirect(url_for('login'))

    def list_tasks(admin=False):
        sql = 'SELECT t.*, u.nome AS responsavel, c.nome AS contato FROM tarefas t JOIN usuarios u ON u.id=t.usuario_id LEFT JOIN contatos c ON c.id=t.contato_id WHERE 1=1'
        values = []
        if not admin:
            sql += ' AND t.usuario_id=?'
            values.append(g.user['id'])
        busca = request.args.get('busca', '').strip()
        if busca:
            sql += ' AND (t.titulo LIKE ? OR t.descricao LIKE ? OR c.nome LIKE ?)'
            values.extend(['%' + busca + '%'] * 3)
        estado = request.args.get('status', '')
        if estado in STATUS:
            sql += ' AND t.status=?'
            values.append(estado)
        sql += " ORDER BY CASE WHEN t.prazo='' THEN 1 ELSE 0 END, t.prazo, t.id DESC"
        return db().execute(sql, values).fetchall()

    @app.get('/')
    @login_required
    def quadro():
        return render_template('quadro.html', tarefas=list_tasks())

    @app.get('/admin')
    @login_required
    def quadro_admin():
        if not g.user['admin']:
            abort(403)
        return render_template('quadro_admin.html', tarefas=list_tasks(True))

    @app.route('/tarefas/nova', methods=['GET', 'POST'])
    @app.route('/tarefas/<int:tarefa_id>/editar', methods=['GET', 'POST'])
    @login_required
    def editar_tarefa(tarefa_id=None):
        original = owned('tarefas', tarefa_id) if tarefa_id else None
        tarefa = dict(original) if original else dict(titulo='', descricao='', status='pendente', prioridade='media', prazo='', usuario_id=g.user['id'], contato_id=None)
        usuarios = db().execute('SELECT id, nome FROM usuarios ORDER BY nome').fetchall() if g.user['admin'] else [g.user]
        contatos = db().execute('SELECT * FROM contatos ORDER BY nome').fetchall() if g.user['admin'] else db().execute('SELECT * FROM contatos WHERE usuario_id=? ORDER BY nome', (g.user['id'],)).fetchall()
        if request.method == 'POST':
            tarefa.update({key: request.form.get(key, '').strip() for key in ['titulo', 'descricao', 'status', 'prioridade', 'prazo']})
            error = None
            if not tarefa['titulo'] or len(tarefa['titulo']) > 150 or len(tarefa['descricao']) > 5000:
                error = 'Informe um título de até 150 caracteres e descrição de até 5000.'
            if tarefa['status'] not in STATUS or tarefa['prioridade'] not in PRIORIDADES:
                error = 'Selecione status e prioridade válidos.'
            try:
                if tarefa['prazo']:
                    tarefa['prazo'] = date.fromisoformat(tarefa['prazo']).isoformat()
                owner = int(request.form.get('usuario_id', g.user['id'])) if g.user['admin'] else g.user['id']
                contact = int(request.form['contato_id']) if request.form.get('contato_id') else None
                if owner not in [u['id'] for u in usuarios]:
                    raise ValueError()
                if contact and not any(c['id'] == contact and c['usuario_id'] == owner for c in contatos):
                    error = 'Selecione um contato pertencente ao responsável escolhido.'
                tarefa.update(usuario_id=owner, contato_id=contact)
            except ValueError:
                error = 'Verifique a data, o responsável e o contato.'
            if error:
                flash(error, 'erro')
            else:
                values = tuple(tarefa[key] for key in ['titulo', 'descricao', 'status', 'prioridade', 'prazo', 'usuario_id', 'contato_id'])
                if original:
                    db().execute('UPDATE tarefas SET titulo=?, descricao=?, status=?, prioridade=?, prazo=?, usuario_id=?, contato_id=? WHERE id=?', values + (tarefa_id,))
                else:
                    db().execute('INSERT INTO tarefas (titulo, descricao, status, prioridade, prazo, usuario_id, contato_id) VALUES (?, ?, ?, ?, ?, ?, ?)', values)
                db().commit()
                flash('Tarefa salva com sucesso.', 'sucesso')
                return redirect(url_for('quadro_admin' if g.user['admin'] else 'quadro'))
        return render_template('editar_tarefa.html', tarefa=tarefa, edicao=original is not None, usuarios=usuarios, contatos=contatos)

    @app.post('/tarefas/<int:tarefa_id>/status')
    @login_required
    def alterar_status(tarefa_id):
        owned('tarefas', tarefa_id)
        estado = request.form.get('status')
        if estado not in STATUS:
            abort(400)
        db().execute('UPDATE tarefas SET status=? WHERE id=?', (estado, tarefa_id))
        db().commit()
        flash('Status atualizado.', 'sucesso')
        return redirect(url_for('quadro_admin' if g.user['admin'] and request.form.get('origem') == 'admin' else 'quadro'))

    @app.get('/contatos')
    @login_required
    def lista_contatos():
        busca = request.args.get('busca', '').strip()
        contatos = db().execute('SELECT * FROM contatos WHERE usuario_id=? AND (nome LIKE ? OR email LIKE ?) ORDER BY nome', (g.user['id'], '%' + busca + '%', '%' + busca + '%')).fetchall()
        return render_template('contatos.html', contatos=contatos)

    @app.route('/contatos/novo', methods=['GET', 'POST'])
    @app.route('/contatos/<int:contato_id>/editar', methods=['GET', 'POST'])
    @login_required
    def formulario_contato(contato_id=None):
        original = owned('contatos', contato_id) if contato_id else None
        contato = dict(original) if original else dict(nome='', email='', telefone='')
        if request.method == 'POST':
            contato.update({key: request.form.get(key, '').strip() for key in ['nome', 'email', 'telefone']})
            if not contato['nome'] or len(contato['nome']) > 120 or len(contato['email']) > 254 or len(contato['telefone']) > 30 or (contato['email'] and ('@' not in contato['email'] or ' ' in contato['email'])):
                flash('Verifique o nome, o e-mail e o telefone informados.', 'erro')
            else:
                values = (contato['nome'], contato['email'], contato['telefone'])
                if original:
                    db().execute('UPDATE contatos SET nome=?, email=?, telefone=? WHERE id=?', values + (contato_id,))
                else:
                    db().execute('INSERT INTO contatos (nome, email, telefone, usuario_id) VALUES (?, ?, ?, ?)', values + (g.user['id'],))
                db().commit()
                flash('Contato salvo com sucesso.', 'sucesso')
                return redirect(url_for('lista_contatos'))
        return render_template('formulario_contato.html', contato=contato, edicao=original is not None)

    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(400)
    def error_page(error):
        return render_template('erro.html', codigo=error.code), error.code

    return app


if __name__ == '__main__':
    create_app().run()
