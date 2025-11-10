# Demo de Rede Social com Neo4j

Uma aplicação de exemplo que demonstra como combinar **Neo4j** com **Python** para construir funcionalidades típicas de uma rede social. O projeto oferece duas experiências:

* Uma interface de linha de comando para criar usuários, seguir perfis, publicar posts e consultar o feed.
* Uma interface web simples (Flask) para executar as mesmas ações a partir do navegador.

> ⚠️ Este repositório é voltado para fins didáticos. Não utilize as credenciais presentes em exemplos em ambientes públicos.

## Estrutura do projeto

```
.
├── app.py                    # Aplicação Flask com telas de cadastro, login e painel autenticado
├── main.py                   # CLI orientada a comandos para operar a rede social
├── requirements.txt          # Dependências Python
├── social_network/
│   ├── neo4j_client.py       # Wrapper para conectar e executar queries no Neo4j
│   └── service.py            # Regras de negócio e consultas Cypher
└── templates/                # Layout base e páginas HTML utilizadas pelo Flask
```

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
```

> O módulo `python-dotenv` é carregado automaticamente tanto pelo CLI quanto pela aplicação Flask, facilitando o desenvolvimento local.

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

3. Acesse `http://127.0.0.1:5000/` e utilize as telas para registrar-se, fazer login e interagir com a rede.

O painel autenticado permite:

* Seguir outros usuários
* Criar novos posts
* Atualizar o feed com um limite configurável de posts recentes

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

Distribuído sob a licença MIT. Consulte o arquivo `LICENSE` se/quando disponível.
