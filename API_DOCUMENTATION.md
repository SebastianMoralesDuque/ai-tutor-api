# AI Tutor Backend — API Documentation

> **Versión:** 0.1.0  
> **Base URL:** `https://ai-tutor.sebastianmorales.sbs`  
> **AI Provider:** OpenCode Zen — DeepSeek V4 Flash Free (gratis, sin API key)

---

## Tabla de Contenidos

1. [Autenticación](#autenticación)
2. [Endpoints](#endpoints)
   - [Health Check](#health-check)
   - [Usuarios](#usuarios)
   - [Sesión Diaria](#sesión-diaria)
   - [Enviar Respuesta](#enviar-respuesta)
   - [Progreso](#progreso)
   - [Chat Tutor](#chat-tutor)
3. [Modelos de Datos](#modelos-de-datos)
4. [Flujo de Uso](#flujo-de-uso)
5. [Configuración](#configuración)
6. [Errores](#errores)

---

## Autenticación

Actualmente la API no requiere autenticación. Para producción, se recomienda agregar JWT o API keys.

---

## Endpoints

### Health Check

```
GET /health
```

**Respuesta:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

### Usuarios

#### Crear Usuario

```
POST /api/users/
```

**Body:**
```json
{
  "topic": "Python",
  "daily_time": 20
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `topic` | string | Sí | Tema de estudio (máx. 255 caracteres) |
| `daily_time` | integer | No | Minutos diarios de estudio (5–120, default: 20) |

**Respuesta (201):**
```json
{
  "id": "a1b2c3d4e5f6...",
  "topic": "Python",
  "daily_time": 20,
  "created_at": "2026-06-09T14:00:00Z"
}
```

---

#### Obtener Usuario

```
GET /api/users/{user_id}
```

**Parámetros de ruta:**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `user_id` | string | ID del usuario |

**Respuesta (200):**
```json
{
  "id": "a1b2c3d4e5f6...",
  "topic": "Python",
  "daily_time": 20,
  "created_at": "2026-06-09T14:00:00Z"
}
```

---

#### Actualizar Usuario

```
PATCH /api/users/{user_id}
```

**Body (parcial):**
```json
{
  "topic": "Machine Learning",
  "daily_time": 30
}
```

**Respuesta (200):** Objeto usuario actualizado.

---

### Sesión Diaria

> **El endpoint principal.** Genera una lección + quiz personalizado usando IA.

```
POST /api/daily-session
```

**Body:**
```json
{
  "user_id": "a1b2c3d4e5f6..."
}
```

**Respuesta (200):**
```json
{
  "lesson": {
    "title": "Understanding Python: decorators, generics",
    "explanation": "Today we're diving deeper into Python. We'll focus on decorators, generics — areas where you've had some difficulty...",
    "bullets": [
      "Key concept: decorators",
      "Key concept: generics",
      "Review: previous mistake"
    ],
    "example": "For example, in Python, when you encounter decorators, remember to apply the fundamental principle step by step."
  },
  "quiz": [
    {
      "question_id": "q_a1b2c3d4",
      "question": "In the context of Python, what best describes decorators?",
      "options": [
        "The correct understanding of decorators",
        "A common misconception about decorators",
        "An unrelated concept to decorators",
        "None of the above"
      ],
      "answer_type": "multiple_choice"
    }
  ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `lesson.title` | string | Título de la lección |
| `lesson.explanation` | string | Explicación detallada |
| `lesson.bullets` | string[] | Puntos clave |
| `lesson.example` | string | Ejemplo práctico |
| `quiz` | array | Preguntas de opción múltiple (3–5) |
| `quiz[].question_id` | string | ID único de la pregunta |
| `quiz[].question` | string | Texto de la pregunta |
| `quiz[].options` | string[] | 4 opciones de respuesta |

---

### Enviar Respuesta

```
POST /api/submit-answer
```

**Body:**
```json
{
  "user_id": "a1b2c3d4e5f6...",
  "question_id": "q_a1b2c3d4",
  "answer": "The correct understanding of decorators"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user_id` | string | ID del usuario |
| `question_id` | string | ID de la pregunta (del quiz) |
| `answer` | string | Respuesta del usuario (texto exacto de la opción) |

**Respuesta (200):**
```json
{
  "correct": true,
  "feedback": "Correct! Well done.",
  "concept": "decorators",
  "mastery_delta": 10.0,
  "updated_progress": {
    "concept": "decorators",
    "mastery_level": 45.0,
    "correct": true
  }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `correct` | boolean | Si la respuesta es correcta |
| `feedback` | string | Retroalimentación de la IA |
| `concept` | string | Concepto evaluado |
| `mastery_delta` | float | Cambio en nivel de dominio (+10 correcta, -15 incorrecta) |
| `updated_progress` | object | Progreso actualizado del concepto |

---

### Progreso

```
GET /api/progress/{user_id}
```

**Respuesta (200):**
```json
{
  "user_id": "a1b2c3d4e5f6...",
  "topic": "Python",
  "streak": 5,
  "concept_mastery": [
    {
      "concept": "decorators",
      "level": 45.0,
      "last_reviewed": "2026-06-09T14:30:00Z"
    },
    {
      "concept": "generics",
      "level": 20.0,
      "last_reviewed": "2026-06-08T14:00:00Z"
    }
  ],
  "recent_mistakes": [
    {
      "concept": "generics",
      "error_description": "Not quite. The answer is: The correct understanding...",
      "question_text": "q_x1y2z3w4",
      "user_answer": "A common misconception",
      "timestamp": "2026-06-08T14:15:00Z"
    }
  ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `streak` | integer | Días consecutivos de estudio |
| `concept_mastery` | array | Nivel de dominio por concepto (0–100) |
| `recent_mistakes` | array | Últimos 5 errores |

---

### Chat Tutor

> **Chat libre con el tutor IA.** Incluye contexto del historial del estudiante.

```
POST /api/chat
```

**Body:**
```json
{
  "user_id": "a1b2c3d4e5f6...",
  "message": "¿Puedes explicarme los decoradores con un ejemplo?"
}
```

**Respuesta (200):**
```json
{
  "response": "¡Buena pregunta sobre Python! He notado que has tenido dificultad con decoradores. Un decorador es esencialmente una función que toma otra función y retorna una nueva función..."
}
```

---

## Modelos de Datos

### Usuario
```
id          : string (UUID hex)
topic       : string
daily_time  : integer (minutos)
created_at  : datetime (UTC)
```

### Concepto
```
id   : string (UUID hex)
name : string (único)
```

### UserConcept (Dominio)
```
user_id       : string (FK → User)
concept_id    : string (FK → Concept)
mastery_level : float (0–100)
last_reviewed : datetime | null
next_review   : datetime | null (spaced repetition)
```

### Error (Mistake)
```
user_id           : string (FK → User)
concept_id        : string (FK → Concept)
error_description : text
question_text     : text
user_answer       : text
timestamp         : datetime
```

---

## Flujo de Uso

```
1. POST /api/users/          → Crear usuario, obtener user_id
2. POST /api/daily-session   → Obtener lección + quiz del día
3. POST /api/submit-answer   → Enviar cada respuesta (repetir por cada pregunta)
4. GET  /api/progress/{id}   → Ver progreso y racha
5. POST /api/chat            → Preguntar al tutor sobre dudas
```

**Ciclo diario:**
```
┌─────────────────────────────────────────┐
│  1. App solicita sesión diaria           │
│  2. Backend genera lección + quiz        │
│  3. Usuario responde preguntas           │
│  4. Backend evalúa y actualiza dominio   │
│  5. Spaced repetition agenda próximo     │
│     review basado en rendimiento         │
└─────────────────────────────────────────┘
```

---

## Configuración

### Variables de Entorno (.env)

```env
# Base de datos
DATABASE_URL=sqlite:///./ai_tutor.db

# IA — OpenCode Zen (DeepSeek V4 Flash Free)
AI_PROVIDER=opencode
AI_API_KEY=tu-api-key-aqui
AI_MODEL=deepseek-v4-flash-free
AI_BASE_URL=https://opencode.ai/zen/v1

# Spaced Repetition
REVIEW_INTERVAL_BASE_HOURS=24
MASTERY_INCREASE_ON_CORRECT=10.0
MASTERY_DECREASE_ON_WRONG=-15.0
```

### Obtener API Key de OpenCode

1. Ir a [opencode.ai](https://opencode.ai)
2. Crear cuenta gratuita
3. Ir a Settings → API Keys
4. Crear una nueva API key
5. Copiarla en `.env` como `AI_API_KEY`

### Cambiar a PostgreSQL

```env
DATABASE_URL=postgresql://user:password@localhost:5432/ai_tutor
```

---

## Errores

| Código | Descripción |
|--------|-------------|
| `200` | Éxito |
| `201` | Recurso creado |
| `400` | Petición inválida |
| `404` | Usuario no encontrado |
| `422` | Error de validación (Pydantic) |
| `500` | Error interno del servidor |

**Formato de error:**
```json
{
  "detail": "User not found"
}
```

---

## Spaced Repetition — Cómo Funciona

El sistema adapta la frecuencia de revisión según el rendimiento:

| Condición | Acción |
|-----------|--------|
| Respuesta correcta | +10 dominio, próxima revisión se aleja |
| Respuesta incorrecta | -15 dominio, próxima revisión en 1 hora |
| Concepto nuevo | Se agrega al pool de estudio |
| Dominio < 40 | Se prioriza en la sesión diaria |
| Sin revisar recientemente | Se agenda para review |

**Fórmula de intervalo:**
```
next_review = now + (base_hours × (1 + mastery_level / 50))
```

- Dominio 0 → revisión en 24h
- Dominio 50 → revisión en 36h
- Dominio 100 → revisión en 72h

---

## Ejemplo Completo (cURL)

```bash
API="https://ai-tutor.sebastianmorales.sbs"

# 1. Crear usuario
curl -X POST $API/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"topic": "Python", "daily_time": 20}'

# Respuesta: {"id": "abc123", ...}

# 2. Obtener sesión diaria
curl -X POST $API/api/daily-session \
  -H "Content-Type: application/json" \
  -d '{"user_id": "abc123"}'

# 3. Enviar respuesta
curl -X POST $API/api/submit-answer \
  -H "Content-Type: application/json" \
  -d '{"user_id": "abc123", "question_id": "q_xyz", "answer": "The correct understanding of decorators"}'

# 4. Ver progreso
curl $API/api/progress/abc123

# 5. Chat con tutor
curl -X POST $API/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "abc123", "message": "Explícame los decoradores"}'
```

---

## Ejemplo con Python (requests)

```python
import requests

BASE = "https://ai-tutor.sebastianmorales.sbs"

# Crear usuario
r = requests.post(f"{BASE}/api/users/", json={
    "topic": "Python",
    "daily_time": 20
})
user = r.json()
user_id = user["id"]

# Sesión diaria
r = requests.post(f"{BASE}/api/daily-session", json={"user_id": user_id})
session = r.json()

print(f"Lección: {session['lesson']['title']}")
for q in session["quiz"]:
    print(f"\nPregunta: {q['question']}")
    for i, opt in enumerate(q["options"]):
        print(f"  {i+1}. {opt}")

# Responder primera pregunta
r = requests.post(f"{BASE}/api/submit-answer", json={
    "user_id": user_id,
    "question_id": session["quiz"][0]["question_id"],
    "answer": session["quiz"][0]["options"][0]
})
result = r.json()
print(f"\n{'✓' if result['correct'] else '✗'} {result['feedback']}")

# Ver progreso
r = requests.get(f"{BASE}/api/progress/{user_id}")
progress = r.json()
print(f"\nRacha: {progress['streak']} días")
print(f"Conceptos: {len(progress['concept_mastery'])}")
```

---

*Generado para AI Tutor Backend v0.1.0 — OpenCode Zen / DeepSeek V4 Flash Free*
