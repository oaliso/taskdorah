# Gerenciador de Tarefas

Aplicação web para criar, acompanhar e compartilhar tarefas entre pessoas. Cada tarefa tem título, descrição, status, prioridade, prazo, criador e responsável. Quem quiser atribuir tarefas a outras pessoas precisa primeiro adicioná-las como contatos.

## Funcionalidades

- **Contas:** registro e login por e-mail ou nome de usuário, com senha armazenada como hash.
- **Quadro de tarefas:** colunas por status, separadas em "Atribuídas a você" e "Atribuídas a outras pessoas", ordenadas por prazo. Clicar em um cartão abre uma janela com os detalhes.
- **Tarefas:** criar, editar, alterar status e excluir, com regras de permissão (veja abaixo).
- **Prazos:** o prazo precisa ser uma data futura. Tarefas com prazo vencido e ainda abertas aparecem como **Atrasada**.
- **Contatos:** envio de solicitação por e-mail ou nome de usuário, aceitar, recusar e remover. O menu mostra um contador de solicitações pendentes.
- **Painel do administrador:** visão de todas as tarefas, cartões de resumo, filtro por status (inclusive "Atrasadas") e troca rápida de status.
- **Aparência:** modo automático, claro ou escuro, e quatro paletas (Índigo, Oceano, Rosa e Daltonismo). Os status usam cor e símbolo, para não depender só da cor.
- **Formulários que preservam o rascunho:** em caso de erro de validação, o que foi digitado não se perde, e o campo com problema (por exemplo, o prazo) fica destacado.

## Tecnologias

Python, Flask, Flask-Login, Flask-SQLAlchemy (SQLite), Jinja2 e Bootstrap 5, mais CSS próprio em `static/static.css`.

## Como executar

Dentro da pasta `gerenciador_de_tarefas`:

```bash
python -m venv venv
# Windows (PowerShell):  .\venv\Scripts\Activate.ps1
# Linux/macOS:           source venv/bin/activate

pip install flask flask-sqlalchemy flask-login
python app.py
```

Acesse `http://127.0.0.1:5000`.

- O banco SQLite é criado automaticamente na primeira execução (`db.create_all()`).
- `create_all()` não altera tabelas existentes. Se o modelo mudar, apague o arquivo `gerenciador_de_tarefas.db` (fica na pasta `instance/`) e rode de novo.
- **Chave secreta:** em ambiente real, defina a variável de ambiente `SECRET_KEY`. Sem ela, o app usa uma chave de desenvolvimento e registra um aviso.
  - PowerShell: `$env:SECRET_KEY = "uma-chave-longa-e-aleatoria"`
  - Linux/macOS: `export SECRET_KEY="uma-chave-longa-e-aleatoria"`

### Dados de demonstração

```bash
python seed_demo.py
```

Cria três usuários, contatos já aceitos entre eles e tarefas em cada status, incluindo uma atrasada. Pode ser executado de novo para restaurar os dados de demonstração (ele apaga e recria as tarefas e os contatos desses três usuários).

| Usuário | Cargo | Senha |
| --- | --- | --- |
| `admin_demo` | admin | `demo123` |
| `ana_demo` | usuário | `demo123` |
| `bruno_demo` | usuário | `demo123` |

Para tornar outro usuário administrador, altere a coluna `cargo` dele para `admin` no banco. Não existe tela para isso.

## Regras de permissão

| Ação | Criador | Responsável | Admin |
| --- | :---: | :---: | :---: |
| Ver a tarefa | sim | sim | sim |
| Editar título, descrição, prioridade e prazo | sim | não | sim |
| Alterar o status | sim | sim | sim |
| Excluir | sim | não | sim |

As regras são verificadas no servidor, e não apenas escondidas na interface.

**Atribuição:** um usuário comum só pode atribuir tarefas a si mesmo ou a contatos aceitos. O administrador pode atribuir a qualquer pessoa.

## Contatos

- Uma solicitação tem três estados: pendente, aceito e recusado.
- Não é possível adicionar a si mesmo nem duplicar uma solicitação pendente.
- Uma solicitação recusada pode ser reenviada.
- Ao **remover** um contato, as tarefas que um tinha atribuído ao outro voltam para o criador, para ninguém ficar com acesso a tarefas de quem deixou de ser contato.

## Status e prazos

- Status guardados: **Pendente**, **Em andamento**, **Concluída** e **Cancelada**. Toda tarefa nova começa como Pendente.
- **Atrasada** não é um status guardado: é calculada quando o prazo venceu e a tarefa não está Concluída nem Cancelada. Ela aparece como selo e destaque no quadro, e como cartão de resumo e filtro no painel admin. Assim, a tarefa nunca fica "presa" em atrasada depois de concluída.
- O prazo precisa ser futuro ao criar. Ao editar, manter o prazo antigo (mesmo já vencido) não gera erro.
- O quadro atualiza o selo de atraso sem recarregar a página quando o prazo de um cartão aberto vence.

## Estrutura

``` none
gerenciador_de_tarefas/
├── app.py            # rotas, regras de permissão e validações
├── models.py         # Usuario, Tarefa e Contato
├── extensions.py     # instância do SQLAlchemy
├── seed_demo.py      # dados de demonstração
├── static/
│   ├── static.css    # temas, paletas e componentes
│   └── atraso.js     # atualiza o selo "Atrasada" no quadro
└── templates/
    ├── base.html, login.html, registro.html
    ├── quadro.html, quadro_admin.html
    ├── adicionar_tarefa.html, editar_tarefa.html
    └── contatos.html, contatos_form.html
```

## Limitações conhecidas

- **Sem proteção CSRF.** Os formulários POST (inclusive aceitar, recusar e remover contatos) não usam token. Em produção, adicionar Flask-WTF/CSRFProtect.
- `app.run(debug=True)` é só para desenvolvimento.
- **SQLite e chaves estrangeiras:** o `PRAGMA foreign_keys` não está ativado, então o `ondelete='CASCADE'` de `Contato` não vale no nível do banco. Como o app não tem exclusão de usuários, isso não afeta o uso atual.
- A senha mínima é de 4 caracteres, escolha pensada para a demonstração.
- Datas e horas usam o horário local do servidor, sem fuso.
- Remover um contato devolve ao criador as tarefas atribuídas entre os dois, mas não há aviso para a outra pessoa.

## Equipe

| Integrante | Tarefas | Contribuição |
| --- | --- | --- |
| Alisson | 2, 4, 5, 6, 9, 15, 18, 21, 26 | Repositório, modelos (`Usuario`, `Tarefa`, `Contato`), telas de login, registro, adicionar e editar tarefa, status e cores, visualização do quadro e aviso de solicitações pendentes |
| Álvaro | 3, 8, 11, 17, 20, 27, 29 | Estrutura de pastas, `static.css`, `app.py`, rotas de contatos, regras de permissão e atribuição, preservação de rascunho nos formulários e README |
| Arthur | 7, 10, 16, 19, 22, 25 | `quadro.html`, `quadro_admin.html`, telas de contatos, seleção de contato ao adicionar tarefa, ajustes no painel admin e `seed_demo.py` (com o tratamento de tarefas de contatos removidos) |

Planejamento, testes de integração e de fluxo, definição de funcionalidades extras, code freeze e entrega foram feitos por todos.
