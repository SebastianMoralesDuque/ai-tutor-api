# AI Tutor Backend — API Documentation

> **Versión:** 0.2.0  
> **Base URL:** `https://ai-tutor.sebastianmorales.sbs`  
> **AI Provider:** OpenCode Zen — DeepSeek V4 Flash Free (gratis, sin API key)

---

## Tabla de Contenidos

1. [Autenticación](#autenticación)
2. [Conceptos clave](#conceptos-clave)
3. [Endpoints](#endpoints)
   - [Health Check](#health-check)
   - [Usuarios](#usuarios)
   - [Sesión Diaria](#sesión-diaria)
   - [Enviar Respuesta](#enviar-respuesta)
   - [Progreso](#progreso)
   - [Chat Tutor](#chat-tutor)
   - [Sugerencias](#sugerencias)
4. [Ciclo de aprendizaje](#ciclo-de-aprendizaje)
5. [Modelos de Datos](#modelos-de-datos)
6. [Flujo de Uso](#flujo-de-uso)
7. [Configuración](#configuración)
8. [Errores](#errores)

---

## Autenticación

Actualmente la API no requiere autenticación. Los usuarios se identifican por UUID.

---

## Conceptos clave

| Concepto | Descripción |
|---|---|
| **Topic** | El tema general que el usuario elige (ej: "ontología", "solipsismo") |
| **Concepto** | Sub-división dentro del topic. Cada topic tiene 3: fundamentals, practice, advanced |
| **Ciclo** | 3 conceptos × 3 días = 9 días por topic |
| **Día** | Cada vez que el usuario llama a `/daily-session`, avanza un día |

```
Topic: "ontología" (9 días total)
├── Concepto 0: ontología fundamentals  → día 1, 2, 3
├── Concepto 1: ontología practice      → día 4, 5, 6
└── Concepto 2: ontología advanced      → día 7, 8, 9
    └── Topic completado → usuario elige nuevo topic
```

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
  "version": "0.2.0"
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
  "topic": "ontología",
  "daily_time": 15
}
```

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `topic` | string | Sí | Tema de estudio (máx. 255 caracteres) |
| `daily_time` | integer | No | Minutos diarios de estudio (5–120, default: 20) |

**Respuesta (201):**
```json
{
  "id": "fd3878bf89f7...",
  "current_topic": "ontología",
  "daily_time": 15,
  "current_concept_index": 0,
  "concept_day": 1,
  "created_at": "2026-06-10T20:41:15.410970"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `current_topic` | string | Topic activo |
| `current_concept_index` | int | 0=fundamentals, 1=practice, 2=advanced |
| `concept_day` | int | Día actual dentro del concepto (1, 2, 3) |

---

#### Obtener Usuario

```
GET /api/users/{user_id}
```

**Respuesta (200):** Igual que crear usuario.

---

#### Actualizar Usuario

```
PATCH /api/users/{user_id}
```

**Body (parcial):**
```json
{
  "current_topic": "epistemología",
  "daily_time": 30
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `current_topic` | string | Cambiar topic (crea topic_progress automáticamente) |
| `daily_time` | int | Cambiar tiempo de estudio |

**Respuesta (200):** Objeto usuario actualizado.

---

### Sesión Diaria

> **El endpoint principal.** Genera lección + quiz para el concepto actual del usuario. Avanza el ciclo automáticamente.

```
POST /api/daily-session
```

**Body:**
```json
{
  "user_id": "fd3878bf89f7..."
}
```

**Respuesta (200):**
```json
{
  "lesson": {
    "title": "Fundamentos de la Ontología",
    "explanation": "La ontología es la rama de la filosofía que estudia la naturaleza del ser...",
    "bullets": [
      "La ontología estudia qué entidades existen",
      "Se divide en ontología general y especial",
      "Los problemas ontológicos fundamentales incluyen..."
    ],
    "example": "Un ejemplo clásico es la pregunta: ¿existen los números o son una construcción humana?"
  },
  "quiz": [
    {
      "question_id": "q_349ed59f",
      "question": "¿Qué estudia principalmente la ontología?",
      "options": [
        "La naturaleza del ser y la existencia",
        "Las reglas del lógico formal",
        "La estructura del argumento válido",
        "Los métodos de investigación científica"
      ],
      "correct_answer_index": 0,
      "answer_type": "multiple_choice"
    },
    {
      "question_id": "q_65bec42e",
      "question": "¿Cuál de los siguientes NO es un componente típico?",
      "options": [
        "Categorías ontológicas",
        "Relaciones de dependencia",
        "Teoremas matemáticos",
        "Niveles de realidad"
      ],
      "correct_answer_index": 2,
      "answer_type": "multiple_choice"
    },
    {
      "question_id": "q_d095f75b",
      "question": "¿En qué área se aplica la ontología?",
      "options": [
        "Filosofía y metafísica",
        "Biología molecular",
        "Ingeniería de software",
        "Contabilidad"
      ],
      "correct_answer_index": 0,
      "answer_type": "multiple_choice"
    }
  ],
  "cycle_info": {
    "topic": "ontología",
    "concept": "ontología fundamentals",
    "concept_index": 0,
    "day_in_cycle": 1,
    "total_concepts": 3,
    "topic_completed": false
  }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `lesson` | object | Lección del día |
| `lesson.title` | string | Título de la lección |
| `lesson.explanation` | string | Explicación detallada |
| `lesson.bullets` | string[] | Puntos clave |
| `lesson.example` | string | Ejemplo práctico |
| `quiz` | array | 3 preguntas de opción múltiple |
| `quiz[].question_id` | string | ID único (usar en submit-answer) |
| `quiz[].question` | string | Texto de la pregunta |
| `quiz[].options` | string[] | 4 opciones |
| `quiz[].correct_answer_index` | int | Índice de la respuesta correcta (0-3) |
| `cycle_info` | object | Estado del ciclo de aprendizaje |
| `cycle_info.topic` | string | Topic actual |
| `cycle_info.concept` | string | Concepto estudiado hoy |
| `cycle_info.concept_index` | int | 0, 1, o 2 |
| `cycle_info.day_in_cycle` | int | 1, 2, o 3 |
| `cycle_info.topic_completed` | bool | `true` solo cuando se completan los 9 días |

**Side effects:**
- Crea registro en `learning_sessions`
- Crea registros en `quiz_questions`
- Avanza `concept_day` o `current_concept_index`
- Si es día 3 del último concepto, marca topic como "completed" y resetea el user

---

### Enviar Respuesta

```
POST /api/submit-answer
```

**Body:**
```json
{
  "user_id": "fd3878bf89f7...",
  "question_id": "q_349ed59f",
  "answer": "0"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user_id` | string | ID del usuario |
| `question_id` | string | ID de la pregunta (del quiz) |
| `answer` | string | `"0"`, `"1"`, `"2"`, `"3"` o `"a"`, `"b"`, `"c"`, `"d"` |

**Respuesta (200):**
```json
{
  "correct": true,
  "feedback": "¡Correcto! Bien hecho.",
  "concept": "ontología fundamentals",
  "mastery_delta": 10.0,
  "updated_progress": {
    "concept": "ontología fundamentals",
    "mastery_level": 10.0,
    "correct": true
  }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `correct` | boolean | Si la respuesta es correcta |
| `feedback` | string | Retroalimentación de la IA |
| `concept` | string | Concepto evaluado |
| `mastery_delta` | float | +10 correcta, -15 incorrecta |
| `updated_progress` | object | Progreso actualizado |

**Nota:** La validación se hace comparando el índice en la DB (sin AI). AI solo genera feedback cuando la respuesta es incorrecta.

---

### Progreso

```
GET /api/progress/{user_id}
```

**Respuesta (200):**
```json
{
  "user_id": "fd3878bf89f7...",
  "current_topic": "ontología",
  "streak": 3,
  "cycle": {
    "concept_index": 0,
    "day_in_cycle": 2,
    "total_concepts": 3,
    "days_per_concept": 3
  },
  "topic_progress": {
    "topic": "ontología",
    "status": "in_progress",
    "concepts_completed": 0,
    "started_at": "2026-06-10T20:41:15"
  },
  "concept_mastery": [
    {
      "concept": "ontología fundamentals",
      "level": 75.0,
      "sessions_done": 1,
      "completed": false,
      "is_current": true
    },
    {
      "concept": "ontología practice",
      "level": 0.0,
      "sessions_done": 0,
      "completed": false,
      "is_current": false
    },
    {
      "concept": "ontología advanced",
      "level": 0.0,
      "sessions_done": 0,
      "completed": false,
      "is_current": false
    }
  ],
  "completed_topics": [
    {
      "topic": "filosofía antigua",
      "completed_at": "2026-06-05T12:00:00"
    }
  ],
  "recent_mistakes": [
    {
      "concept": "ontología fundamentals",
      "error_description": "Casi, pero no es correcta...",
      "question_text": "¿Qué estudia principalmente la ontología?",
      "user_answer": "2",
      "timestamp": "2026-06-10T21:30:00"
    }
  ]
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `current_topic` | string | Topic activo |
| `streak` | int | Días consecutivos de estudio |
| `cycle` | object | Estado del ciclo actual |
| `cycle.concept_index` | int | Qué concepto (0, 1, 2) |
| `cycle.day_in_cycle` | int | Qué día (1, 2, 3) |
| `topic_progress` | object | Progreso del topic actual |
| `topic_progress.status` | string | `"in_progress"` o `"completed"` |
| `topic_progress.concepts_completed` | int | 0 a 3 |
| `concept_mastery` | array | Nivel por concepto |
| `concept_mastery[].is_current` | bool | Es el concepto activo |
| `concept_mastery[].sessions_done` | int | Días estudiados (0-3) |
| `completed_topics` | array | Historial de temas completados |
| `recent_mistakes` | array | Últimos 5 errores |

---

### Chat Tutor

> **Chat libre con el tutor IA.** Incluye contexto del historial, áreas débiles y memoria del usuario.

```
POST /api/chat
```

**Body:**
```json
{
  "user_id": "fd3878bf89f7...",
  "message": "¿Puedes explicarme la ontología con un ejemplo?"
}
```

**Respuesta (200):**
```json
{
  "response": "¡Buena pregunta sobre ontología! Has estado estudiando los fundamentos. La ontología es la rama de la filosofía que pregunta qué cosas existen..."
}
```

---

### Sugerencias

> **Sugerencias personalizadas** basadas en: temas estudiados, áreas débiles, intereses del usuario.

```
POST /api/suggestions
```

**Body:**
```json
{
  "user_id": "fd3878bf89f7..."
}
```

**Respuesta (200):**
```json
[
  "Ética",
  "Lógica Formal",
  "Escepticismo"
]
```

| Nota | Descripción |
|------|-------------|
| No sugiere | Temas ya completados por el usuario |
| Prioriza | Áreas débiles identificadas en quizzes |
| Formato | Array de exactamente 3 strings (1-2 palabras cada uno) |

---

## Ciclo de aprendizaje

### Flujo completo

```
1. POST /api/users/               → Crear usuario con topic
2. POST /api/daily-session        → Día 1: fundamentals
3. POST /api/submit-answer ×3     → Responder quiz
4. POST /api/daily-session        → Día 2: fundamentals (refuerzo)
5. POST /api/submit-answer ×3
6. POST /api/daily-session        → Día 3: fundamentals (evaluación)
7. POST /api/submit-answer ×3
   └── fundamentals completado → avanza a practice
8. POST /api/daily-session        → Día 4: practice
   ... (repetir 3 días más)
11. POST /api/daily-session       → Día 7: advanced
    ... (repetir 3 días más)
14. Topic completado → cycle_info.topic_completed = true
15. POST /api/suggestions         → Obtener sugerencias
16. PATCH /api/users/{id}         → Cambiar a nuevo topic
17. Repetir desde paso 2
```

### Avance automático

| Día | concept_day | concept_index | Concepto |
|-----|-------------|---------------|----------|
| 1 | 1 | 0 | fundamentals |
| 2 | 2 | 0 | fundamentals |
| 3 | 3 | 0 | fundamentals |
| 4 | 1 | 1 | practice |
| 5 | 2 | 1 | practice |
| 6 | 3 | 1 | practice |
| 7 | 1 | 2 | advanced |
| 8 | 2 | 2 | advanced |
| 9 | 3 | 2 | advanced |

Después del día 9:
- `topic_progress.status` → `"completed"`
- `user.current_topic` → `""` (reseteado)
- `user_memory.topics_studied` → agrega el topic completado

---

## Modelos de Datos

### Users
```
id                    : string (UUID hex, PK)
daily_time            : integer (minutos)
current_topic         : string
current_concept_index : integer (0, 1, 2)
concept_day           : integer (1, 2, 3)
concept_start_date    : datetime | null
created_at            : datetime (UTC)
```

### Concepts
```
id   : string (UUID hex, PK)
name : string (único, ej: "ontología fundamentals")
```

### UserConcepts
```
id            : string (UUID hex, PK)
user_id       : string (FK → Users)
concept_id    : string (FK → Concepts)
mastery_level : float (0–100)
sessions_done : integer (0–3)
completed     : boolean
last_reviewed : datetime | null
next_review   : datetime | null
```

### TopicProgress
```
id                   : string (UUID hex, PK)
user_id              : string (FK → Users)
topic                : string
status               : string ("in_progress" | "completed")
concepts_completed   : integer (0–3)
started_at           : datetime
completed_at         : datetime | null
```

### UserMemory
```
id             : string (UUID hex, PK)
user_id        : string (FK → Users, unique)
interests      : text (JSON array)
weak_areas     : text (JSON array)
topics_studied : text (JSON array)
learning_style : text
notes          : text
updated_at     : datetime
```

### LearningSessions
```
id                : string (UUID hex, PK)
user_id           : string (FK → Users)
topic             : string
concept_name      : string
day_in_cycle      : integer (1, 2, 3)
date              : datetime
concepts_covered  : text
```

### QuizQuestions
```
id                    : string (UUID hex, PK)
session_id            : string (FK → LearningSessions)
user_id               : string (FK → Users)
question_index        : integer
question              : text
options               : text (JSON array de 4 strings)
correct_answer_index  : integer (0–3)
concept               : string
created_at            : datetime
```

### Mistakes
```
id                : string (UUID hex, PK)
user_id           : string (FK → Users)
concept_id        : string (FK → Concepts)
error_description : text
question_text     : text
user_answer       : text
timestamp         : datetime
```

---

## Configuración

### Variables de Entorno (.env)

```env
# Base de datos
DATABASE_URL=sqlite:////app/data/ai_tutor.db

# IA — OpenCode Zen (sin API key)
AI_PROVIDER=opencode
AI_MODEL=deepseek-v4-flash-free
AI_BASE_URL=https://opencode.ai/zen/v1

# Spaced Repetition
REVIEW_INTERVAL_BASE_HOURS=24
MASTERY_INCREASE_ON_CORRECT=10.0
MASTERY_DECREASE_ON_WRONG=-15.0
```

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

## Ejemplo Completo (cURL)

```bash
API="https://ai-tutor.sebastianmorales.sbs"

# 1. Crear usuario
curl -X POST $API/api/users/ \
  -H "Content-Type: application/json" \
  -d '{"topic": "ontología", "daily_time": 15}'
# Respuesta: {"id": "fd3878bf...", ...}

# 2. Obtener sesión diaria (Día 1)
curl -X POST $API/api/daily-session \
  -H "Content-Type: application/json" \
  -d '{"user_id": "fd3878bf..."}'
# Respuesta: {lesson, quiz, cycle_info}

# 3. Enviar respuestas
curl -X POST $API/api/submit-answer \
  -H "Content-Type: application/json" \
  -d '{"user_id": "fd3878bf...", "question_id": "q_349ed59f", "answer": "0"}'

# 4. Ver progreso
curl $API/api/progress/fd3878bf...

# 5. Chat con tutor
curl -X POST $API/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "fd3878bf...", "message": "Explícame la ontología"}'

# 6. Obtener sugerencias
curl -X POST $API/api/suggestions \
  -H "Content-Type: application/json" \
  -d '{"user_id": "fd3878bf..."}'
# Respuesta: ["Ética", "Lógica", "Epistemología"]

# 7. Cambiar topic (después de completar uno)
curl -X PATCH $API/api/users/fd3878bf... \
  -H "Content-Type: application/json" \
  -d '{"current_topic": "epistemología"}'
```

---

*API Documentation — AI Tutor Backend v0.2.0 — OpenCode Zen / DeepSeek V4 Flash Free*
