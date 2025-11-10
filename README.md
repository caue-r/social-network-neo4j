# Neo4j Social Network Demo

Uma aplicação simples em Python que demonstra como construir uma pequena rede social usando Neo4j.

## Pré-requisitos

1. Python 3.10+
2. Variáveis de ambiente configuradas com as credenciais do Neo4j (adicione-as ao seu shell ou crie um arquivo `.env` baseado em `.env.example`):
   ```bash
   export NEO4J_URI=neo4j+s://5e6000fc.databases.neo4j.io
   export NEO4J_USERNAME=neo4j
   export NEO4J_PASSWORD=2DNfpgWWArMyhYP3FTkaAgfUwnjGNdM-oh6siy9L2_g
   export NEO4J_DATABASE=neo4j
   ```
3. Instalar dependências:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## Como usar

A aplicação expõe um utilitário de linha de comando (`main.py`). Exemplos:

### Criar usuário
```bash
python main.py create-user alice "Alice Silva" --bio "Apaixonada por grafos"
```

### Seguir outro usuário
```bash
python main.py follow alice bob
```

### Listar quem um usuário segue
```bash
python main.py list-following alice
```

### Criar um post
```bash
python main.py create-post alice "Olá, Neo4j!"
```

### Buscar o feed de um usuário
```bash
python main.py feed alice --limit 10
```

Todos os comandos retornam JSON para facilitar integrações.

## Estrutura do projeto

- `main.py`: Interface de linha de comando.
- `social_network/neo4j_client.py`: Cliente reutilizável do Neo4j.
- `social_network/service.py`: Regras de negócio da rede social.
- `requirements.txt`: Dependências Python necessárias.
