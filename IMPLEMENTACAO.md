# ObiterJus — API de Minutas: Projeto de Implementação

## Visão Geral

API intermediária que recebe peças jurídicas em PDF, processa via IA, e devolve ao app apenas o conteúdo estruturado — nunca o PDF bruto.

---

## Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|--------|-----------|--------------|
| Linguagem | Python 3.12 | Ecossistema maduro para PDF e IA |
| Framework | FastAPI | Async nativo, validação Pydantic, docs automáticos |
| Servidor | Uvicorn + Gunicorn | ASGI performático para uploads |
| IA | Anthropic Claude API (claude-opus-4-7) | Interpretação semântica jurídica |
| PDF | pdfplumber + pymupdf | Extração de texto com layout |
| Armazenamento efêmero | Redis (TTL 15min) | Descarte automático do PDF bruto |
| Fila de processamento | Celery + Redis | Processamento assíncrono de documentos grandes |
| Autenticação | JWT (python-jose) | Identificação da extensão/app |
| Validação de schema | Pydantic v2 | Campos obrigatórios e marcação de incerteza |
| Observabilidade | structlog + Sentry | Trilha de auditoria mínima |

---

## Estrutura de Pastas

```
obiter-minuta-api/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Entrypoint FastAPI
│   ├── config.py                # Settings via env vars
│   ├── dependencies.py          # Auth, Redis, Celery
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── ingest.py            # POST /ingest
│   │   ├── result.py            # GET /result/{job_id}
│   │   └── status.py            # GET /status/{job_id}
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── converter.py         # PDF → texto estruturado
│   │   ├── semantic.py          # Interpretação com Claude
│   │   ├── validator.py         # Validação do schema de saída
│   │   └── packager.py          # Montagem do pacote final
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── input.py             # IngestRequest, FileMetadata
│   │   └── output.py            # MinutaPackage, ConfidenceField
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── process.py           # Task Celery: pipeline completo
│   │
│   └── utils/
│       ├── __init__.py
│       ├── audit.py             # Log de auditoria
│       └── sanitizer.py         # Limpeza de texto jurídico
│
├── tests/
│   ├── test_ingest.py
│   ├── test_semantic.py
│   └── test_validator.py
│
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Rotas da API

### `POST /ingest`

Recebe o PDF e dispara o pipeline de processamento.

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data
```

**Body (form-data):**
| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `file` | File (PDF) | Sim | Peça jurídica |
| `tipo_declarado` | string | Sim | inicial / contestação / tutela / réplica / recurso / outro |
| `numero_processo` | string | Não | CNJ format |
| `vara` | string | Não | Identificação da vara |
| `origem` | string | Não | ID da extensão ou sessão |

**Response 202 Accepted:**
```json
{
  "job_id": "j_abc123xyz",
  "status": "queued",
  "estimated_seconds": 30
}
```

---

### `GET /status/{job_id}`

Consulta o estado do processamento.

**Response 200:**
```json
{
  "job_id": "j_abc123xyz",
  "status": "processing",
  "stage": "semantic_analysis",
  "progress_pct": 65,
  "created_at": "2026-05-20T14:30:00Z"
}
```

**Valores de `status`:** `queued` | `processing` | `completed` | `failed`

**Valores de `stage`:** `conversion` | `semantic_analysis` | `validation` | `packaging` | `done`

---

### `GET /result/{job_id}`

Retorna o pacote estruturado. Disponível apenas com `status: completed`. O resultado é descartado do cache após a primeira leitura ou TTL de 2h.

**Response 200:** ver "Schema de Saída" abaixo.

**Response 404:** job expirado ou não encontrado.

---

### `DELETE /job/{job_id}` *(opcional)*

Descarte explícito antecipado. Confirma remoção imediata do Redis.

---

## Schema de Entrada — `IngestRequest`

```python
class IngestRequest(BaseModel):
    tipo_declarado: TipoPeca
    numero_processo: str | None = None
    vara: str | None = None
    origem: str | None = None

class TipoPeca(str, Enum):
    inicial = "inicial"
    contestacao = "contestacao"
    tutela = "tutela"
    replica = "replica"
    recurso = "recurso"
    outro = "outro"
```

---

## Schema de Saída — `MinutaPackage`

```json
{
  "job_id": "j_abc123xyz",
  "versao_schema": "1.0",
  "processado_em": "2026-05-20T14:30:45Z",

  "metadados": {
    "tipo_detectado": "contestacao",
    "tipo_declarado": "contestacao",
    "tipo_confirmado": true,
    "numero_processo": "0001234-56.2026.8.26.0100",
    "vara": "3ª Vara Cível de São Paulo",
    "paginas_originais": 22,
    "origem": "ext-session-9f3a"
  },

  "markdown": "# Contestação\n\n## I. Preliminares\n...",

  "estrutura": {
    "partes": {
      "requerente": {
        "valor": "João da Silva",
        "confianca": 0.97,
        "origem_trecho": "p.1, parágrafo 2"
      },
      "requerido": {
        "valor": "Empresa XYZ Ltda.",
        "confianca": 0.95,
        "origem_trecho": "p.1, parágrafo 2"
      }
    },

    "preliminares": [
      {
        "titulo": "Ilegitimidade passiva",
        "texto": "A requerida não integra a cadeia de responsabilidade...",
        "confianca": 0.91,
        "origem_trecho": "p.3, §1"
      }
    ],

    "fatos": [
      {
        "sequencia": 1,
        "texto": "Em 10/03/2026, o autor celebrou contrato...",
        "confianca": 0.88,
        "origem_trecho": "p.5, §3"
      }
    ],

    "teses": [
      {
        "titulo": "Ausência de dano moral",
        "fundamento_legal": ["Art. 186 CC", "Súmula 227 STJ"],
        "texto": "Não restou comprovado o nexo causal...",
        "confianca": 0.85,
        "origem_trecho": "p.9, §2"
      }
    ],

    "pedidos": [
      {
        "tipo": "principal",
        "texto": "Julgamento improcedente da ação",
        "confianca": 0.98,
        "origem_trecho": "p.20, §1"
      },
      {
        "tipo": "subsidiario",
        "texto": "Redução do valor da condenação",
        "confianca": 0.93,
        "origem_trecho": "p.20, §2"
      }
    ],

    "provas": [
      {
        "tipo": "documental",
        "descricao": "Contrato social da requerida",
        "referencia_doc": "Doc. 3",
        "confianca": 0.99,
        "origem_trecho": "p.12, rodapé"
      }
    ]
  },

  "qualidade": {
    "confianca_geral": 0.87,
    "campos_incertos": [
      {
        "campo": "fatos[2].texto",
        "motivo": "Trecho ilegível no PDF original",
        "confianca": 0.42
      }
    ],
    "lacunas": [
      "Data da audiência não localizada no documento",
      "Valor da causa não declarado explicitamente"
    ],
    "requer_revisao": true
  },

  "auditoria": {
    "hash_arquivo_entrada": "sha256:e3b0c44298fc1c14...",
    "modelo_ia": "claude-opus-4-7",
    "versao_conversor": "1.2.0",
    "pdf_descartado": true
  }
}
```

---

## Modelo Pydantic — Campos com Confiança

```python
from pydantic import BaseModel, Field
from typing import Generic, TypeVar

T = TypeVar("T")

class ConfidenceField(BaseModel, Generic[T]):
    valor: T
    confianca: float = Field(ge=0.0, le=1.0)
    origem_trecho: str | None = None

class Pedido(BaseModel):
    tipo: Literal["principal", "subsidiario", "honorarios", "outro"]
    texto: str
    confianca: float
    origem_trecho: str | None = None

class QualidadeOutput(BaseModel):
    confianca_geral: float
    campos_incertos: list[CampoIncerto]
    lacunas: list[str]
    requer_revisao: bool

class MinutaPackage(BaseModel):
    job_id: str
    versao_schema: str = "1.0"
    processado_em: datetime
    metadados: Metadados
    markdown: str
    estrutura: EstruturaPeca
    qualidade: QualidadeOutput
    auditoria: Auditoria
```

---

## Pipeline de Processamento

```
[POST /ingest]
      │
      ▼
  Salva PDF no Redis (TTL 15min)
  Cria job_id, status = queued
  Dispara task Celery
      │
      ▼
  [Task: converter.py]
  PDF → texto bruto via pdfplumber
  Detecta layout (colunas, cabeçalhos, rodapés)
  Gera Markdown estrutural
      │
      ▼
  [Task: semantic.py]
  Prompt para Claude com:
  - Markdown da peça
  - Tipo declarado
  - Schema esperado como JSON
  Claude retorna JSON estruturado
      │
      ▼
  [Task: validator.py]
  Valida schema via Pydantic
  Marca campos com confiança < 0.7 como incertos
  Gera lista de lacunas
      │
      ▼
  [Task: packager.py]
  Monta MinutaPackage final
  Calcula confiança geral (média ponderada)
  Grava resultado no Redis (TTL 2h)
  Descarta PDF bruto do Redis
  Status = completed
      │
      ▼
  [GET /result/{job_id}]
  App/extensão consome o pacote
  Após leitura ou TTL: auto-expira
```

---

## Dependências — `requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
gunicorn==22.0.0
pydantic[email]==2.8.0
pydantic-settings==2.4.0

# Upload e processamento de arquivos
python-multipart==0.0.9

# PDF
pdfplumber==0.11.0
pymupdf==1.24.0

# IA
anthropic==0.34.0

# Fila e cache
celery==5.4.0
redis==5.1.0

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Observabilidade
structlog==24.4.0
sentry-sdk[fastapi]==2.13.0

# Dev/teste
pytest==8.3.0
pytest-asyncio==0.24.0
httpx==0.27.0
```

---

## Variáveis de Ambiente — `.env.example`

```env
# App
APP_ENV=development
SECRET_KEY=change_me_in_production
API_VERSION=v1

# IA
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-opus-4-7

# Redis
REDIS_URL=redis://localhost:6379/0
JOB_TTL_MINUTES=15
RESULT_TTL_HOURS=2

# Limites
MAX_PDF_SIZE_MB=50
MAX_PAGES=150

# Observabilidade
SENTRY_DSN=
LOG_LEVEL=INFO
```

---

## Regras de Implementação

1. **PDF nunca persiste** — armazenado apenas em Redis com TTL; deletado após `packaging` com confirmação no campo `auditoria.pdf_descartado: true`.
2. **Campos incertos são marcados, não inventados** — confiança < 0.7 vai para `qualidade.campos_incertos`.
3. **Trilha de auditoria mínima** — todo job registra `hash_arquivo_entrada`, `modelo_ia`, `versao_conversor`.
4. **Sem texto livre solto** — toda saída passa pelo schema Pydantic; resposta sem schema válido retorna erro 422.
5. **Tipo detectado vs. declarado** — Claude reconfirma o tipo; divergência fica em `metadados.tipo_confirmado: false`.
6. **Processamento assíncrono** — uploads retornam 202 imediatamente; cliente faz polling em `/status/{job_id}`.

---

## Critérios de Aceitação

| Critério | Verificação |
|----------|-------------|
| PDF não retorna ao app | `auditoria.pdf_descartado: true` em todo resultado |
| Campos incertos visíveis | `qualidade.campos_incertos` nunca vazio quando confiança < 0.7 |
| Rastreabilidade | `origem_trecho` presente em ≥ 90% dos campos extraídos |
| Processamento < 60s | p95 para peças até 30 páginas |
| Schema válido sempre | Validator rejeita qualquer saída que não passe no Pydantic |
| Envio com poucos cliques | Extensão só precisa de: arquivo + tipo_declarado |
