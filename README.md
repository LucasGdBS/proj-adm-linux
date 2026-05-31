# Infraestrutura Local com Docker Compose

Ambiente de monitoramento com balanceamento de carga, banco de dados persistente e stack de observabilidade completa.

## Arquitetura

```
                        ┌─────────────────────────────────────┐
                        │          Rede Interna Docker         │
                        │                                      │
Internet ──► Nginx:80 ──┼──► app1:8000  ◄── Prometheus:9090  │
                        │──► app2:8000  ◄── cAdvisor:8080     │
                        │──► Grafana:3000                      │
                        │         │                            │
                        │      db:5432 (PostgreSQL)            │
                        └─────────────────────────────────────┘
```

Apenas o Nginx possui porta exposta no host. Todos os demais serviços se comunicam exclusivamente pela rede interna `internal`.

## Serviços

| Serviço      | Imagem                          | Função                                              |
|--------------|---------------------------------|-----------------------------------------------------|
| `nginx`      | `nginx:alpine`                  | Reverse proxy e load balancer                       |
| `app1`       | build local (`./app`)           | Instância 1 da API FastAPI                          |
| `app2`       | build local (`./app`)           | Instância 2 da API FastAPI                          |
| `db`         | `postgres:16-alpine`            | Banco de dados PostgreSQL com volume persistente    |
| `prometheus` | `prom/prometheus`               | Coleta de métricas das apps e dos contêineres       |
| `grafana`    | `grafana/grafana`               | Visualização de métricas                            |
| `cadvisor`   | `gcr.io/cadvisor/cadvisor`      | Métricas de CPU e memória dos contêineres           |

## Pré-requisitos

- Docker Engine com o plugin Compose v2 (`docker compose`) **ou** `docker-compose` v1
- Porta 80 disponível no host

## Inicialização

1. Copie o arquivo de exemplo e ajuste as variáveis se necessário:

```bash
cp .env.example .env
```

2. Suba o ambiente:

```bash
bash scripts/start-infra.sh
```

O script:
1. Verifica se o Docker está rodando
2. Detecta automaticamente `docker compose` ou `docker-compose`
3. Detecta se o ambiente já está em execução (evita subir em duplicata)
4. Executa `docker compose up -d --build`
5. Exibe o status dos contêineres ao final

### Outros comandos úteis

```bash
# Derrubar tudo
docker compose down

# Derrubar e apagar volumes (perde dados do banco)
docker compose down -v

# Ver logs em tempo real
docker compose logs -f

# Ver logs de um serviço específico
docker compose logs -f app1
```

## Acesso

| Serviço  | URL                          | Credenciais              |
|----------|------------------------------|--------------------------|
| API      | http://localhost             | —                        |
| Grafana  | http://localhost/grafana/    | admin / admin            |

> O Grafana já sobe com o Prometheus configurado como datasource padrão (provisionamento automático em `grafana/provisioning/`).

## API — Endpoints

| Método | Path      | Descrição                                           |
|--------|-----------|-----------------------------------------------------|
| GET    | `/`       | Mensagem de boas-vindas com o hostname da instância |
| GET    | `/health` | Status da aplicação e conectividade com o banco     |
| GET    | `/items`  | Lista todos os itens do banco                       |
| POST   | `/items`  | Cria um novo item (`{"name": "..."}`)               |
| GET    | `/metrics`| Métricas Prometheus (contagem de requisições)       |

### Métricas expostas pela API

A lib `prometheus-fastapi-instrumentator` instrumenta automaticamente todas as rotas e expõe os dados em `/metrics`. O endpoint `/metrics` em si é excluído da contagem para não inflar os números.

Métricas principais:

- `http_requests_total` — total de requisições por rota, método e status HTTP
- `http_request_duration_seconds` — histograma de latência por rota

### Exemplo de saída de `/metrics`

```
http_requests_total{handler="/",method="GET",status="2xx"} 42
http_requests_total{handler="/health",method="GET",status="2xx"} 10
http_request_duration_seconds_bucket{handler="/",le="0.005"} 39
```

## Monitoramento

### Prometheus

O Prometheus coleta métricas a cada 15 segundos dos seguintes alvos (configurados em `prometheus/prometheus.yml`):

| Job              | Alvo             | O que coleta                        |
|------------------|------------------|-------------------------------------|
| `fastapi-app1`   | `app1:8000`      | Requisições HTTP, latência          |
| `fastapi-app2`   | `app2:8000`      | Requisições HTTP, latência          |
| `cadvisor`       | `cadvisor:8080`  | CPU, memória e I/O dos contêineres  |
| `prometheus`     | `localhost:9090` | Auto-monitoramento do Prometheus    |

### cAdvisor

Coleta métricas de runtime dos contêineres diretamente do Docker. Métricas relevantes no Grafana:

- `container_cpu_usage_seconds_total` — uso de CPU por contêiner
- `container_memory_usage_bytes` — uso de memória por contêiner

### Grafana

Acesse `http://localhost/grafana/` e crie dashboards usando o datasource **Prometheus** (já configurado). Sugestões de queries para começar:

```promql
# Requisições por segundo na app1
rate(http_requests_total{job="fastapi-app1"}[1m])

# Uso de memória dos contêineres
container_memory_usage_bytes{name=~"app.*|nginx|db"}

# Latência p99 da API
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

## Estrutura de Arquivos

```
.
├── app/
│   ├── main.py             # Aplicação FastAPI
│   ├── requirements.txt    # Dependências Python
│   └── Dockerfile
├── nginx/
│   └── nginx.conf          # Reverse proxy + load balancer
├── prometheus/
│   └── prometheus.yml      # Configuração de scraping
├── grafana/
│   └── provisioning/
│       └── datasources/
│           └── prometheus.yml  # Datasource provisionado automaticamente
├── scripts/
│   └── start-infra.sh      # Script de inicialização
├── docker-compose.yml
└── .env                    # Variáveis de ambiente (não versionar em produção)
```

## Variáveis de Ambiente

Definidas no `.env` e carregadas automaticamente pelo Compose:

| Variável            | Descrição                        | Padrão  |
|---------------------|----------------------------------|---------|
| `POSTGRES_USER`     | Usuário do banco                 | `admin` |
| `POSTGRES_PASSWORD` | Senha do banco                   | `secret`|
| `POSTGRES_DB`       | Nome do banco de dados           | `appdb` |
| `GRAFANA_PASSWORD`  | Senha do admin do Grafana        | `admin` |

> Em produção, não versione o `.env`. Use secrets do Docker ou variáveis de ambiente do sistema.

## Persistência

Os dados do PostgreSQL são armazenados em `./data/` no host (bind mount), mapeado para `/var/lib/postgresql/data` dentro do contêiner. O diretório persiste independente de `docker compose down` — para apagar os dados basta remover a pasta `data/`.

O mesmo vale para `prometheus_data` e `grafana_data` (dashboards e configurações salvas no Grafana).

### Por que a pasta `data/` parece vazia?

Ao subir pela primeira vez, o PostgreSQL inicializa o diretório e aplica permissão `700` com dono UID 999 (usuário `postgres` dentro do container). Por isso o seu usuário do host não consegue listar o conteúdo diretamente:

```bash
ls data/
# ls: cannot open directory 'data/': Permission denied
```

Para inspecionar o conteúdo é necessário `sudo`:

```bash
sudo ls data/
# PG_VERSION  base  global  pg_hba.conf  pg_ident.conf  ...
```

Ou acessar de dentro do próprio container, sem precisar de sudo:

```bash
docker compose exec db ls /var/lib/postgresql/data
```

Os dados estão lá e persistidos — a restrição é só de permissão no host.
