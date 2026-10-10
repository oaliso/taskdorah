# Taskdorah

Aplicação acadêmica Flask para tarefas e contatos. Usa SQLite, sem Docker ou servidor de banco externo. Python 3.10 ou superior.

## Executar

Na raiz do repositório:

```bash
python -m venv .venv
```

Ative o ambiente no Windows com `.venv\Scripts\activate`, ou no Linux/macOS com `source .venv/bin/activate`.

```bash
python -m pip install -r requirements.txt
python -m flask --app gerenciador_de_tarefas.app criar-usuario Arthur
python -m flask --app gerenciador_de_tarefas.app criar-usuario Administrador --admin
python gerenciador_de_tarefas/app.py
```

Os comandos de criação solicitam uma senha de pelo menos 8 caracteres, com confirmação. Não há contas ou senhas padrão. Acesse http://127.0.0.1:5000 e entre com uma das contas criadas. Para outros integrantes, repita `criar-usuario Nome`.

## Funcionalidades

- `editar_tarefa.html`: criação e edição, título, descrição, prazo, prioridade, status e contato.
- `quadro.html`: tarefas do usuário em quatro colunas, busca, filtros e atualização de status.
- `quadro_admin.html`: tarefas da equipe, indicadores filtrados, edição e atribuição de responsável.
- `contatos.html` e `formulario_contato.html`: busca, cadastro e edição de contatos pessoais.
- Contatos vinculados devem pertencer ao responsável pela tarefa. O administrador pode selecionar contatos de todos os responsáveis ao editar tarefas.
- Tarefas pendentes/em andamento com prazo anterior ao dia atual são destacadas como atrasadas.
- Layout responsivo, estados vazios, labels acessíveis e CSS local, sem dependência de CDN.

O backend e a base estavam vazios; foi incluída a infraestrutura mínima para executar e validar as telas. As permissões são verificadas no servidor; usuários comuns só acessam suas tarefas e contatos. O admin pode gerenciar todas as tarefas. Senhas são armazenadas com hash; formulários usam token CSRF.

Dados e chave de sessão ficam em `gerenciador_de_tarefas/instance/`, ignorados pelo Git. O servidor usa o fuso horário da máquina para avaliar prazos. O comando de execução é destinado a desenvolvimento local; hospedagem pública requer configuração própria de servidor, HTTPS e proteção contra tentativas repetidas de login.

## Testes

```bash
python -m unittest discover -s tests -v
```
