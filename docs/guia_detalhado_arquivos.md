# Guia detalhado de arquivos

Este documento descreve em profundidade o papel de cada arquivo do projeto, destacando responsabilidades, funções principais e como cada componente se integra ao restante da solução.

## Raiz do repositório

### `app.py`
Aplicação Flask responsável pela experiência web completa. Destaques:
- **Configuração**: carrega variáveis de ambiente com `load_dotenv()`, aplica `SECRET_KEY` para a sessão, lê credenciais administrativas (`ADMIN_USERNAME`/`ADMIN_PASSWORD`).
- **Acesso ao Neo4j**: o context manager `get_client()` instancia `Neo4jClient`, garante fechamento com `finally` e é reutilizado por todas as rotas que interagem com o banco.
- **Autorização**: decorators `login_required` e `admin_required` checam `session['auth_user']` e `session['is_admin']`, exibindo `flash()` e redirecionando quando o usuário não tem permissão.
- **Helpers de renderização**: `render_dashboard()` e `render_admin_dashboard()` montam contexto padrão (feed vazio, resultados de busca, sugestões, estado admin) para reduzir repetição na hora de renderizar `dashboard.html` e `admin.html`.
- **Formatação de datas**: filtro `short_datetime` usado nos templates converte strings ISO em formato amigável, recorrendo ao helper `_normalize_iso_datetime()` para truncar frações e normalizar timezones.
- **Rotas públicas**: `/`, `/login`, `/register` exibem formulários iniciais e redirecionam usuários já autenticados.
- **Fluxo autenticado**: rotas protegidas com `login_required` (`/dashboard`, `/profile`, `/create-user`, `/follow`, `/unfollow`, `/profile/bio`, `/create-post`, `/delete-post`, `/feed`) manipulam formulários HTML, chamam funções da camada de serviço para executar ações (seguindo/desfazendo follow, criando posts, atualizando bio, listando feed) e exibem mensagens de sucesso/erro.
- **Autenticação**: `/register` gera hash com `generate_password_hash` antes de chamar `service.register_account`; `/login` compara hashes com `check_password_hash` e popula `session['auth_user']`; `/logout` limpa sessão de usuário e também o modo admin.
- **Administração**: `/admin` exibe painel com busca avançada (`service.admin_search_users`), `/admin/login` e `/admin/logout` controlam o modo administrador, enquanto `/admin/users/create`, `/admin/users/update` e `/admin/users/delete` executam CRUD completo com validações (como troca de username, redefinição opcional de senha, exclusão com `service.admin_delete_user`).

### `main.py`
Interface de linha de comando que reutiliza a camada de serviço:
- **Gerenciamento de driver**: `get_client()` repete o padrão de contexto garantindo fechamento do driver após cada comando.
- **Handlers específicos**: cada subcomando (`create-user`, `follow`, `list-following`, `create-post`, `feed`) possui um handler dedicado que chama a função correspondente em `service` e imprime o resultado em JSON legível (`indent=2`, `default=str` para datas UUID).
- **CLI declarativa**: `build_parser()` define a mensagem de ajuda, subparsers, argumentos obrigatórios/opcionais (como `--bio` e `--limit`) e vincula cada subparser ao handler correto via `set_defaults(func=...)`.
- **Entrada principal**: `main()` analisa argumentos (`parser.parse_args()`) e executa o handler associado.

### `requirements.txt`
Lista de dependências Python necessárias: Flask e Werkzeug (servidor web e hashing), Neo4j Python Driver (acesso ao banco), python-dotenv (carregar `.env`), entre outras bibliotecas de suporte.

### `README.md`
Documentação introdutória com visão geral do projeto, requisitos, passos de instalação, instruções da CLI, execução do app Flask, descrição resumida de diretórios e próximos passos sugeridos.

### `LICENSE`
Licença MIT que regula o uso, cópia e distribuição do código-fonte.

## Pacote `social_network/`

### `social_network/neo4j_client.py`
Abstração de acesso ao banco Neo4j:
- **`Neo4jConfig`**: dataclass que lê `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`; lança `RuntimeError` se faltar variável obrigatória.
- **Classe `Neo4jClient`**: construtor cria `GraphDatabase.driver` com autenticação básica; `execute_write()` e `execute_read()` executam queries, convertem `Record` em dicionários Python e retornam também contadores (`nodes_created`, `relationships_created` etc.).
- **Tratamento de erros**: método interno `_run()` abre uma sessão (opcionalmente em banco específico), executa callback e captura `Neo4jError`, propagando como `RuntimeError("Neo4j query failed")` para simplificar o tratamento na camada superior.

### `social_network/service.py`
Camada de domínio com todas as operações do produto:
- **Usuários**:
  - `create_user()` usa `MERGE` para criar ou atualizar usuários, mantém `username_lower` e retorna o nó completo.
  - `register_account()` valida unicidade de username/email antes de criar novos usuários com `id`, `email_lower`, `password_hash` e `created_at`.
  - `find_user_for_login()` localiza usuário por username/email (case-insensitive) e retorna `password_hash` para validação.
  - `get_user_profile()` retorna dados completos do perfil (nome, email, bio, data de criação).
  - `update_user_bio()` atualiza apenas a bio do usuário atual.
  - `_ensure_unique_identity()` é helper reutilizado para garantir que trocas de username/email não colidam com outros perfis.
- **Relacionamentos**:
  - `add_follow()` cria relacionamento `[:FOLLOWS]` e registra data (`since`).
  - `remove_follow()` desfaz o relacionamento de follow, lançando erro amigável quando a relação não existe.
  - `list_following()` e `list_followers()` retornam listas ordenadas alfabeticamente com username, nome e bio das conexões.
  - `suggest_users_to_follow()` sorteia (`rand()`) perfis não seguidos, limitando o total retornado.
- **Postagens**:
  - `create_post()` cria nós `Post` com `randomUUID()` e timestamp `datetime()` ligados ao autor.
  - `list_user_posts()` lista todos os posts de um usuário ordenados por `created_at DESC`.
  - `delete_post()` garante que apenas o dono apague o post, retornando erro quando inexistente ou pertencente a outro usuário.
- **Feed e buscas**:
  - `fetch_feed()` agrega posts do usuário e de quem ele segue, com fallback que checa se o viewer existe para diferenciar "sem posts" de "usuário inexistente".
  - `search_users()` permite que usuários busquem perfis por fragmentos de nome/username.
  - `admin_search_users()` amplia o escopo para email e aumenta o limite padrão, pensado para o painel admin.
- **Administração**:
  - `admin_create_user()` cria contas completas incluindo senha inicial, aplicando `_ensure_unique_identity` para username/email.
  - `admin_update_user()` atualiza seletivamente username, nome, email, bio e senha, montando dinamicamente os `SET` e validando campos vazios.
  - `admin_delete_user()` remove usuário e posts associados usando `DETACH DELETE`.

## Diretório `templates/`
Conjunto de templates Jinja2 que compõem a interface web. Todos estendem `base.html`, herdando cabeçalho, mensagens `flash` e estrutura comum.

### `templates/base.html`
Estrutura base do site: define `<header>` com nome "ConectaGraph", menu do usuário autenticado com dropdown controlado por script inline (abre/fecha ao clicar fora), área central `<main>` que exibe mensagens `flash` e injeta conteúdo via `{% block content %}`.

### `templates/index.html`
Página inicial pública que exibe lado a lado dois formulários completos:
- **Cadastro rápido** com campos obrigatórios (`name`, `email`, `username`, `password`) enviando POST para `/register`.
- **Login rápido** com `identifier` e `password` enviando POST para `/login`.
Serve como landing page para visitantes ainda não autenticados.

### `templates/login.html`
Tela dedicada de login para usuários existentes:
- Reaproveita `base.html` e centraliza um formulário `auth-form` que envia para `/login`.
- Inclui links de ação rápida para criar conta (`/register`) e acessar a área administrativa (`/admin`).

### `templates/register.html`
Página de cadastro detalhado:
- Formulário `auth-form` envia POST para `/register`, exige todos os campos e define mínimo de 4 caracteres para senha.
- Área de links oferece retorno fácil para a tela de login.

### `templates/dashboard.html`
Painel principal após login:
- **Cabeçalho interno** com busca (`GET /dashboard?search=`) e atalho para `/profile`.
- **Resultados de busca** exibem cards com bio, botões de seguir/deixar de seguir e manutenção da query (`redirect_search`).
- **Post box** permite publicar novos posts via `/create-post`.
- **Feed** mostra posts retornados por `service.fetch_feed`, inclui formulário para atualizar o limite (`/feed`) e utiliza o filtro `short_datetime`.
- **Sugestões** no `<aside>` listam perfis recomendados por `service.suggest_users_to_follow`, cada um com botão de seguir.

### `templates/profile.html`
Área "Meu perfil":
- Apresenta resumo do usuário autenticado (nome, username, email, data de criação) com formulário para atualizar a bio (`/profile/bio`).
- Divide a tela em colunas com listas de quem o usuário segue e quem o segue, oferecendo botão de `unfollow` direto.
- Lista todos os posts do usuário em cards, cada um com timestamp formatado e botão "Apagar" que envia para `/delete-post` com `post_id` oculto.

### `templates/admin.html`
Painel exclusivo para administradores:
- Antes do login admin, exibe formulário simples para `/admin/login`.
- Após autenticação, mostra barra de ferramentas com busca (`admin_search_users`) e botão para sair do modo admin.
- Lista resultados de busca em "cards" editáveis com formulário completo para atualizar username, nome, email, bio e senha (POST em `/admin/users/update`) e botão separado para exclusão (POST em `/admin/users/delete` com confirmação JS inline).
- Inclui seção "Adicionar novo usuário" com formulário dedicado para `/admin/users/create`.

## Diretório `static/`

### `static/styles.css`
Folha de estilo global responsável pela identidade visual:
- Define resets básicos e tipografia padrão, customiza botões, inputs, links e mensagens de feedback (`flash-success`, `flash-error`).
- Estrutura o layout do dashboard com grids/flex (`.dashboard-stage`, `.main-dashboard-card`, `.suggestions-card`), cartões (`.panel-card`, `.feed-card`, `.auth-card`), formulários (`.auth-form`, `.search-bar`) e estados vazios (`.empty-feed`).
- Fornece variações de botões (`.secondary-button`, `.danger-button`, `.unfollow-button`, `.small-button`).
- Contém media queries que reorganizam colunas para visão mobile/tablet, garantindo responsividade.
- Inclui utilitários de acessibilidade como `.sr-only` para rótulos visuais e `.profile-dropdown.open` para menu do usuário.

## Diretório `docs/`
Destinado à documentação complementar. Contém este arquivo (`guia_detalhado_arquivos.md`) e pode receber futuros guias técnicos ou arquiteturais.
