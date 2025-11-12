# Demo de Rede Social com Neo4j

Uma aplicação de exemplo que demonstra como combinar **Neo4j** com **Python** para construir funcionalidades típicas de uma rede social. O projeto oferece duas experiências: uma interface web em Flask e uma CLI para automações.

> ⚠️ Este repositório é voltado para fins didáticos. Não utilize as credenciais presentes em exemplos em ambientes públicos.

## Guia de arquivos do projeto

A tabela a seguir explica, arquivo a arquivo, a função de cada parte do repositório.

### Raiz do repositório

| Caminho | Função |
| --- | --- |
| `LICENSE` | Texto da licença MIT que rege o uso do código-fonte. |
| `README.md` | Documento que apresenta o projeto, instruções de execução e o mapa de arquivos (este arquivo). |
| `requirements.txt` | Lista as dependências Python necessárias para rodar a aplicação e a CLI. |
| `app.py` | Implementa a aplicação **Flask**, incluindo rotas web públicas, autenticadas e administrativas, além dos filtros de template usados nas páginas. |
| `main.py` | Expõe a interface de linha de comando com comandos para criar usuários, seguir perfis, publicar posts e consultar o feed. |

### Módulo `social_network/`

| Caminho | Função |
| --- | --- |
| `social_network/neo4j_client.py` | Abstrai a criação do driver oficial do Neo4j, centraliza a leitura das variáveis de ambiente e oferece métodos utilitários para executar queries Cypher com segurança. |
| `social_network/service.py` | Camada de regras de negócio: operações de cadastro de usuários, relacionamentos de follow/unfollow, publicação de posts, buscas, feed e autenticação. Compartilhada tanto pela web quanto pela CLI. |

### Diretório `templates/`

| Caminho | Função |
| --- | --- |
| `templates/base.html` | Layout base utilizado por todas as páginas. Define cabeçalho, área de mensagens flash e inclui o CSS principal. |
| `templates/index.html` | Página inicial pública com formulários de registro e login rápidos. |
| `templates/login.html` | Página dedicada de login com formulário simples de autenticação. |
| `templates/register.html` | Página dedicada de registro com campos de nome, email, usuário e senha. |
| `templates/dashboard.html` | Dashboard autenticado: busca de usuários, sugestões para seguir, feed de posts, formulário de publicação e controles de follow/unfollow. |
| `templates/profile.html` | Exibe e permite editar dados do perfil autenticado (bio, seguidores, seguindo e posts próprios). |
| `templates/admin.html` | Painel administrativo protegido: autenticação de administrador, busca e edição de usuários, redefinição de senha e exclusão de contas. |

### Diretório `static/`

| Caminho | Função |
| --- | --- |
| `static/styles.css` | Folha de estilo global responsável pelo visual das páginas (layout responsivo, cartões, formulários e feedback visual). |

## Funcionalidades principais

- Cadastro e autenticação web com Flask, incluindo busca de usuários, follow/unfollow, criação de posts e feed com controle de limite.
- Tela de perfil com edição de bio, listagem de seguidores/seguidos e histórico completo de posts.
- Painel administrativo protegido por senha (`/admin`) para criar, atualizar, redefinir senha e excluir usuários.
- CLI (`main.py`) que expõe os comandos essenciais para automatizações e integrações.
- Camada de serviço compartilhada (`social_network/service.py`) que centraliza as regras de negócio e consultas Cypher utilizadas por todas as interfaces.

## Pré-requisitos

1. **Python 3.10 ou superior**
2. Um banco **Neo4j 5.x** acessível (AuraDB ou instância local)
3. [Pip](https://pip.pypa.io/) e (opcionalmente) `python -m venv` para isolar dependências

### Variáveis de ambiente

As credenciais de acesso ao Neo4j são obtidas via variáveis de ambiente. Crie um arquivo `.env` na raiz do projeto com os valores adequados:

```env
NEO4J_URI=neo4j+s://<host>.databases.neo4j.io
NEO4J_USERNAME=<usuario>
NEO4J_PASSWORD=<senha>
NEO4J_DATABASE=neo4j            # opcional: nome do banco (use quando não for o default)
FLASK_SECRET_KEY=troque-esta-chave
ADMIN_USERNAME=admin            # opcional: usuário do painel /admin (default: admin)
ADMIN_PASSWORD=troque-esta-senha # opcional: senha do painel /admin (default: admin)
```

> O módulo `python-dotenv` é carregado automaticamente tanto pelo CLI quanto pela aplicação Flask, facilitando o desenvolvimento local.
> Para evitar uso dos valores padrão em ambientes acessíveis, ajuste `ADMIN_USERNAME` e `ADMIN_PASSWORD`.

### Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

## Executando a interface de linha de comando

O script `main.py` disponibiliza os comandos abaixo. Todos retornam JSON para facilitar integração com outras ferramentas.

| Comando | Descrição |
| --- | --- |
| `python main.py create-user <username> <nome> [--bio "..."]` | Cria ou atualiza um perfil |
| `python main.py follow <username> <alvo>` | Cria um relacionamento `FOLLOWS` |
| `python main.py list-following <username>` | Lista quem o usuário segue |
| `python main.py create-post <username> "conteúdo"` | Publica um post |
| `python main.py feed <username> [--limit N]` | Consulta o feed agregando posts próprios e de quem segue |

Exemplo rápido:

```bash
python main.py create-user alice "Alice Silva" --bio "Apaixonada por grafos"
python main.py create-user bob "Bob Santos"
python main.py follow alice bob
python main.py create-post bob "Olá, Neo4j!"
python main.py feed alice --limit 5
```

## Executando a interface web

1. Configure as variáveis de ambiente (ou `.env`) conforme descrito acima.
2. Inicie o servidor Flask:

   ```bash
   flask --app app run --debug
   ```

3. Acesse `http://127.0.0.1:5000/`, cadastre-se em `/register`, faça login em `/login` e utilize o dashboard autenticado.

### Painel autenticado

- Buscar usuários por nome/username e seguir ou deixar de seguir perfis diretamente da lista de resultados.
- Publicar posts e atualizar o feed informando o limite desejado de itens.
- Abrir `/profile` para editar a bio, revisar seguidores/seguidos e listar todos os posts do usuário autenticado.
- Efetuar logout com segurança (encerra também o modo administrador ativo).

### Painel do administrador

- Acesse `http://127.0.0.1:5000/admin` e informe `ADMIN_USERNAME`/`ADMIN_PASSWORD` configurados no `.env` (os valores padrão `admin`/`admin` servem apenas para desenvolvimento local).
- Busque usuários por nome, email ou username, altere campos (incluindo redefinição de senha) e salve as mudanças.
- Cadastre perfis completos, inclusive bio e email, a partir do formulário dedicado.
- Exclua usuários e posts associados quando precisar limpar o ambiente de testes (a operação é destrutiva).

## Camada de serviço e modelo de dados

A lógica de negócio está concentrada em `social_network/service.py`. Ela utiliza o cliente definido em `social_network/neo4j_client.py`, que centraliza a criação da conexão com o driver oficial do Neo4j e executa as queries Cypher.

Principais elementos do grafo:

* `(:User)` — nós de usuário com propriedades como `username`, `name`, `bio`, `email` e hashes de senha
* `(:Post)` — nós de postagens com `content` e `created_at`
* Relacionamentos `(:User)-[:FOLLOWS]->(:User)` e `(:User)-[:PUBLISHED]->(:Post)`

As funções de serviço encapsulam padrões comuns:

* `create_user` utiliza `MERGE` para criar ou atualizar perfis
* `add_follow` garante idempotência ao relacionar seguidores
* `fetch_feed` agrega posts do usuário e de quem ele segue com ordenação por data
* `register_account` e `find_user_for_login` reforçam unicidade de email/usuário e suportam autenticação

## Próximos passos sugeridos

* Criar testes automatizados para a camada de serviço usando um Neo4j de teste
* Adicionar validações adicionais na interface web (por exemplo, limites de tamanho de bio/post)
* Implementar paginação no feed e histórico de posts via API/CLI

## Licença

Distribuído sob a licença MIT. Consulte o arquivo `LICENSE` para mais detalhes.
