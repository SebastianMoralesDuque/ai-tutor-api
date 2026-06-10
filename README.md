# AI Tutor Backend

Backend RESTful API para una aplicación de tutoría personalizada con inteligencia artificial. Genera lecciones y quizzes adaptativos siguiendo un ciclo de estudio de 3 días por concepto.

## Arquitectura

```
FastAPI + SQLAlchemy + SQLite (PostgreSQL-ready)
AI: DeepSeek V4 Flash Free via OpenCode Zen (sin API key)
```

### Flujo de aprendizaje

Cada topic se divide en 3 conceptos, cada uno estudiado durante 3 días:

```
Topic: "ontología" (9 días total)
├── Día 1-3: ontología fundamentals
├── Día 4-6: ontología practice
└── Día 7-9: ontología advanced
    └── Topic completado → sugerir nuevo topic
```

### Modelo de datos

| Tabla | Descripción |
|---|---|
| `users` | Usuario con estado del ciclo (topic, concepto, día) |
| `concepts` | Conceptos únicos (fundamentals, practice, advanced) |
| `user_concepts` | Mastery por concepto por usuario (0-100) |
| `topic_progress` | Lifecycle de cada topic (in_progress/completed) |
| `user_memory` | Memoria del tutor: intereses, áreas débiles, temas estudiados |
| `learning_sessions` | Registro diario de sesiones |
| `quiz_questions` | Preguntas persistidas para validación |
| `mistakes` | Errores del estudiante con feedback |

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/users/` | Crear usuario |
| `GET` | `/api/users/{id}` | Obtener usuario |
| `PATCH` | `/api/users/{id}` | Actualizar usuario |
| `POST` | `/api/daily-session` | Generar lección + quiz del día |
| `POST` | `/api/submit-answer` | Responder pregunta |
| `GET` | `/api/progress/{id}` | Progreso completo |
| `POST` | `/api/chat` | Chat con tutor |
| `POST` | `/api/suggestions` | Sugerencias personalizadas |
| `GET` | `/health` | Health check |

Documentación completa: [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## Configuración

### Variables de entorno

Copiar `.env.example` a `.env`:

```bash
cp .env.example .env
```

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `sqlite:////app/data/ai_tutor.db` | URL de base de datos |
| `AI_PROVIDER` | `opencode` | `mock` o `opencode` |
| `AI_MODEL` | `deepseek-v4-flash-free` | Modelo de AI |
| `AI_BASE_URL` | `https://opencode.ai/zen/v1` | URL del proveedor AI |

### Desarrollo local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
uvicorn app.main:app --reload --port 8080

# Modo mock (sin red)
AI_PROVIDER=mock uvicorn app.main:app --reload
```

### Docker

```bash
# Build
docker build -t ai-tutor-backend .

# Run
docker run -d --name ai-tutor-backend -p 8080:8080 -v ./data:/app/data ai-tutor-backend
```

### Producción (Docker + Traefik)

```bash
docker run -d \
  --name ai-tutor-backend \
  --restart unless-stopped \
  --network coolify \
  -p 8081:8080 \
  -v /path/to/data:/app/data \
  ai-tutor-backend
```

## Estructura del proyecto

```
app/
├── api/
│   └── routes/
│       ├── user.py           # CRUD de usuarios
│       ├── learning.py       # daily-session, submit-answer, progress
│       ├── chat.py           # Chat con tutor
│       └── suggestions.py    # Sugerencias inteligentes
├── core/
│   ├── config.py             # Settings (env-based)
│   ├── ai_client.py          # OpenCode Zen client (httpx)
│   └── prompt_builder.py     # Prompts en español
├── db/
│   ├── database.py           # Engine + session
│   ├── models.py             # ORM models (8 tablas)
│   └── repository.py         # Data access layer
├── schemas/
│   ├── learning.py           # Request/response schemas
│   ├── progress.py           # Progress + chat schemas
│   ├── user.py               # User schemas
│   └── suggestion.py         # Suggestion schema
├── services/
│   ├── learning_service.py   # Ciclo de aprendizaje
│   ├── progress_service.py   # Agregación de progreso
│   └── tutor_service.py      # Chat con memoria
└── main.py                   # FastAPI app entry point
```

## Tecnologías

- **FastAPI** — Framework web async
- **SQLAlchemy** — ORM con SQLite (PostgreSQL-ready)
- **Pydantic** — Validación de schemas
- **httpx** — Cliente HTTP para AI (sin SDK)
- **DeepSeek V4 Flash Free** — Modelo vía OpenCode Zen (gratis, sin API key)

## Licencia

MIT
