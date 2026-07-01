# FastAPI AI Template

A **production-ready FastAPI backend** for AI applications, supporting OpenAI, Gemini, and local LLMs (Ollama / OpenAI-compatible), with Redis caching, YAML prompt templates, streaming, structured logging, JWT auth, and clean architecture.

---

## ✨ Feature Highlights

| Feature | Details |
|---|---|
| **Multi-provider LLM** | OpenAI, Gemini, Ollama/Local via LiteLLM |
| **Streaming** | Server-Sent Events (`text/event-stream`) |
| **Prompt Templates** | YAML + Jinja2 rendering |
| **Caching** | Redis-backed, toggled by env |
| **Auth** | JWT access + refresh tokens, bcrypt passwords |
| **File Uploads** | Multipart with metadata fields |
| **Middleware** | Request-ID, timing, CORS, error handling |
| **Config** | 100% `.env` driven, typed via pydantic-settings |
| **Testing** | pytest with mocked LLM calls |

---

## 📁 Project Structure

```
app/
├── main.py                     # FastAPI app factory + lifespan hooks
├── core/
│   ├── config.py               # Typed settings from .env
│   ├── logging.py              # JSON structured logging
│   ├── security.py             # JWT + password hashing
│   ├── cors.py                 # CORS middleware setup
│   └── cache.py                # Redis client lifecycle
├── api/
│   ├── deps.py                 # Dependency injection
│   └── v1/
│       ├── router.py           # All v1 routes
│       └── endpoints/
│           ├── health.py       # GET /health, /ready, /version
│           ├── chat.py         # POST /chat, /chat/stream
│           ├── completions.py  # POST /completion, /completion/stream
│           ├── embeddings.py   # POST /embeddings
│           ├── upload.py       # POST /upload
│           ├── files.py        # GET/DELETE /files/{id}
│           ├── auth.py         # POST /auth/login|logout|refresh, GET /auth/me
│           ├── users.py        # CRUD /users
│           └── items.py        # CRUD /items
├── services/
│   ├── llm_service.py          # Provider-agnostic LLM calls
│   ├── prompt_service.py       # YAML prompt loader + Jinja2 renderer
│   ├── cache_service.py        # Redis cache read/write
│   ├── file_service.py         # File upload/retrieval/deletion
│   └── auth_service.py         # Credential verification + token issuance
├── schemas/                    # Pydantic v2 request/response models
├── models/                     # SQLAlchemy ORM models (User, Item)
├── middleware/                 # RequestID, Timing, CacheMiddleware, ErrorHandler
├── prompts/                    # YAML prompt definitions
└── utils/                      # Helpers, hashes, validators
tests/                          # pytest test suite
```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
# Using the project's virtual environment
.venv\Scripts\pip install -r requirements.txt

# Or with pyproject.toml
.venv\Scripts\pip install -e ".[dev]"
```

### 2. Create your `.env` file

```bash
copy .env.example .env
```

Edit `.env` and fill in your API keys:

```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
SECRET_KEY=your-long-random-secret
```

### 3. Run the development server

```bash
.venv\Scripts\uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API docs will be available at: **http://localhost:8000/docs**

---

## 🔧 Configuration Reference

All settings live in `.env`. Key variables:

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_PROVIDER` | `openai` | LLM provider: `openai`, `gemini`, `local` |
| `OPENAI_API_KEY` | — | Your OpenAI API key |
| `GEMINI_API_KEY` | — | Your Gemini API key |
| `LOCAL_BASE_URL` | `http://localhost:11434/v1` | Ollama / local LLM URL |
| `LOCAL_MODEL` | `llama3.2` | Local model name |
| `ENABLE_CACHE` | `false` | Toggle Redis caching |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `ENABLE_STREAMING` | `true` | Enable streaming endpoints |
| `ENABLE_FALLBACK` | `false` | Auto-fallback to another provider |
| `SECRET_KEY` | — | JWT signing secret (change in production!) |

---

## 🤖 Using a Local LLM (Ollama)

1. [Install Ollama](https://ollama.com)
2. Pull a model: `ollama pull llama3.2`
3. Set in `.env`:
   ```env
   DEFAULT_PROVIDER=local
   LOCAL_BASE_URL=http://localhost:11434/v1
   LOCAL_MODEL=llama3.2
   ```

---

## 📡 API Endpoints

### Health

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
curl http://localhost:8000/api/v1/version
```

### Chat Completion

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is FastAPI?"}],
    "provider": "openai",
    "temperature": 0.7,
    "max_tokens": 200
  }'
```

### Streaming Chat

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "stream": true
  }'
```

### Chat with Prompt Template

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [],
    "prompt_name": "summarize",
    "prompt_vars": {
      "input": "FastAPI is a modern Python web framework...",
      "tone": "casual",
      "language": "English"
    }
  }'
```

### Text Completion

```bash
curl -X POST http://localhost:8000/api/v1/completion \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Once upon a time", "max_tokens": 100}'
```

### Embeddings

```bash
curl -X POST http://localhost:8000/api/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello world", "provider": "openai"}'
```

### File Upload

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@document.pdf" \
  -F "prompt=Summarize this document" \
  -F 'metadata={"category": "reports"}'
```

### Authentication

```bash
# Login (returns JWT tokens)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -F "username=admin@example.com" \
  -F "password=admin123"

# Get current user
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### CRUD: Items

```bash
# Create item (requires auth)
curl -X POST http://localhost:8000/api/v1/items \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "My Item", "price": 9.99}'

# List items with pagination
curl "http://localhost:8000/api/v1/items?page=1&size=10" \
  -H "Authorization: Bearer <token>"
```

---

## 🧪 Running Tests

```bash
.venv\Scripts\pytest tests/ -v
```

---

## 🔒 Security Notes

- Change `SECRET_KEY` before deploying to production.
- The demo user store in `auth_service.py` is in-memory — wire it to your database.
- The in-memory CRUD stores in `users.py` / `items.py` are templates — replace with SQLAlchemy DB calls.
- In production, set `ENV=production` to hide `/docs` and `/redoc`.

---

## 🛠️ Extending the Template

### Add a new endpoint
1. Create `app/api/v1/endpoints/my_feature.py`
2. Define an `APIRouter` and handlers
3. Add to `app/api/v1/router.py`

### Add a new prompt
Create `app/prompts/my_prompt.yaml` with `name`, `system`, `template`, and optional parameters.

### Switch providers per request
Pass `"provider": "gemini"` (or `"local"`) in any AI request body.

---

## 📦 Production Deployment

```bash
# Install production dependencies only
pip install -r requirements.txt

# Run with Gunicorn + Uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

Set `ENV=production` and `DEBUG=false` in your production `.env`.
