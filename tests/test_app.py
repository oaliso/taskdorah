import sqlite3
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash
from gerenciador_de_tarefas.app import create_app


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = str(Path(self.temp.name) / 'test.db')
        self.app = create_app({'TESTING': True, 'DATABASE': self.database, 'SECRET_KEY': 'test-key'})
        self.client = self.app.test_client()
        with sqlite3.connect(self.database) as db:
            for name, admin in [('Arthur', 0), ('Outro', 0), ('Admin', 1)]:
                db.execute('INSERT INTO usuarios(nome, senha, admin) VALUES (?, ?, ?)',
                           (name, generate_password_hash('test-password'), admin))

    def tearDown(self):
        self.temp.cleanup()

    def post(self, url, data=None):
        self.client.get('/login')
        with self.client.session_transaction() as session:
            token = session['csrf']
        return self.client.post(url, data={**(data or {}), 'csrf': token}, follow_redirects=True)

    def login(self, name='Arthur'):
        return self.post('/login', {'nome': name, 'senha': 'test-password'})

    def task(self, **changes):
        return self.post('/tarefas/nova', dict(titulo='Entrega de trabalho', descricao='Revisar texto',
                                              status='pendente', prioridade='alta', prazo='2020-01-01', **changes))

    def test_login_and_csrf(self):
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertEqual(self.client.post('/login', data={}).status_code, 400)
        self.assertIn('inválidos', self.post('/login', {'nome': 'Arthur', 'senha': 'wrong'}).text)
        self.assertIn('Meu quadro', self.login().text)
        self.post('/sair')
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_contact_task_edit_and_status_persist(self):
        self.login()
        self.assertIn('sucesso', self.post('/contatos/novo', {'nome': 'Ana', 'email': 'ana@example.com', 'telefone': '9999'}).text)
        response = self.task(contato_id='1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Ana', response.text)
        self.assertIn('Atrasada', response.text)
        self.assertIn('Entrega de trabalho', self.client.get('/tarefas/1/editar').text)
        response = self.post('/tarefas/1/editar', dict(titulo='Entrega revisada', descricao='<script>alert(1)</script>', status='andamento', prioridade='baixa', prazo='', contato_id='1'))
        self.assertIn('Entrega revisada', response.text)
        self.assertNotIn('<script>alert(1)</script>', response.text)
        self.post('/tarefas/1/status', {'status': 'concluida'})
        self.post('/contatos/1/editar', {'nome': 'Ana Silva', 'email': 'ana@example.com', 'telefone': ''})
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT status,contato_id FROM tarefas').fetchone(), ('concluida', 1))
            self.assertEqual(db.execute('SELECT nome FROM contatos').fetchone()[0], 'Ana Silva')
        self.assertIn('Entrega revisada', self.client.get('/?busca=revisada&status=concluida').text)
        self.assertNotIn('Entrega revisada', self.client.get('/?busca=inexistente').text)

    def test_permissions_and_forged_contact(self):
        self.login('Outro')
        self.post('/contatos/novo', {'nome': 'Privado'})
        self.task(contato_id='1')
        self.post('/sair')
        self.login()
        self.assertNotIn('Entrega de trabalho', self.client.get('/').text)
        for url in ['/admin', '/tarefas/1/editar', '/contatos/1/editar']:
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.post('/tarefas/1/status', {'status': 'concluida'}).status_code, 403)
        self.assertIn('pertencente', self.task(contato_id='1').text)
        self.task(usuario_id='2')
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT usuario_id FROM tarefas WHERE id=2').fetchone()[0], 1)

    def test_admin_can_assign_and_edit(self):
        self.login('Outro')
        self.post('/contatos/novo', {'nome': 'Cliente'})
        self.post('/sair')
        self.login('Admin')
        response = self.task(usuario_id='2', contato_id='1')
        self.assertIn('Painel administrativo', response.text)
        self.assertIn('Cliente', response.text)
        self.assertEqual(self.client.get('/tarefas/1/editar').status_code, 200)
        self.assertEqual(self.post('/tarefas/1/status', {'status': 'concluida', 'origem': 'admin'}).status_code, 200)

    def test_validation_and_empty_pages(self):
        self.login()
        for url in ['/', '/contatos', '/contatos/novo', '/tarefas/nova']:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get('/tarefas/999/editar').status_code, 404)
        for changes in [{'titulo': ''}, {'prazo': 'invalid'}, {'status': 'inventado'}, {'prioridade': 'inventada'}]:
            data = dict(titulo='Teste', descricao='', prazo='', status='pendente', prioridade='media')
            data.update(changes)
            self.assertEqual(self.post('/tarefas/nova', data).status_code, 200)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM tarefas').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
