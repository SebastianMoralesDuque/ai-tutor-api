"""
Prompt builder — constructs structured prompts for the AI layer.

All system prompts end with "Answer directly without thinking out loud.
Output ONLY the JSON, no markdown fences, no extra text." because DeepSeek V4
uses reasoning_content internally — if we don't force direct output, all max_tokens
get consumed by thinking and content comes back empty.
"""


def build_lesson_prompt(
    topic: str,
    concepts: list[str],
    mistakes: list[dict],
    daily_time: int,
    day_in_cycle: int = 1,
    concept_type: str = "fundamentals",
) -> dict:
    """
    Build a prompt payload for lesson generation.
    Returns a dict with system + user messages.
    """
    mistake_context = ""
    if mistakes:
        items = "\n".join(
            f"- {m.get('concept', 'unknown')}: {m.get('error_description', '')}"
            for m in mistakes[:5]
        )
        mistake_context = f"\nThe student has made these recent mistakes:\n{items}\n"

    # Day-specific instructions
    day_instructions = {
        1: "This is the FIRST day. Introduce the concept clearly with definitions and basic examples.",
        2: "This is the SECOND day. Reinforce the concept with more examples and common misconceptions.",
        3: "This is the FINAL evaluation day. Review deeply and prepare the student for mastery assessment.",
    }

    type_instructions = {
        "fundamentals": "Focus on core definitions, principles, and foundational understanding.",
        "practice": "Focus on real-world applications, exercises, and hands-on understanding.",
        "advanced": "Focus on deep analysis, edge cases, connections to other concepts, and critical thinking.",
    }

    return {
        "system": (
            "Eres un tutor experto. Genera una lección concisa y estructurada. "
            "La lección debe ser adecuada para una sesión de estudio enfocada. "
            "Devuelve JSON con: title, explanation, bullets (lista), example. "
            "Responde siempre en español. "
            "Responde directamente sin pensar en voz alta. "
            "Salida SOLO el JSON, sin cercas de markdown, sin texto extra."
        ),
        "user": (
            f"Tema: {topic}\n"
            f"Concepto: {concepts[0] if concepts else topic}\n"
            f"Tipo: {concept_type}\n"
            f"Día {day_in_cycle} de 3: {day_instructions.get(day_in_cycle, '')}\n"
            f"Enfoque: {type_instructions.get(concept_type, '')}\n"
            f"Tiempo de estudio: {daily_time} minutos\n"
            f"{mistake_context}"
            "Genera una lección estructurada en formato JSON."
        ),
    }


def build_quiz_prompt(
    topic: str,
    lesson: dict,
    concepts: list[str],
    mistakes: list[dict],
) -> dict:
    """Build a prompt payload for quiz generation."""
    mistake_context = ""
    if mistakes:
        items = "\n".join(
            f"- {m.get('concept', 'unknown')}: {m.get('error_description', '')}"
            for m in mistakes[:3]
        )
        mistake_context = f"\nPast mistakes to review:\n{items}\n"

    return {
        "system": (
            "Eres un generador de cuestionarios educativos. "
            "Genera EXACTAMENTE 3 preguntas de opción múltiple.\n\n"
            "REGLAS ESTRICTAS:\n"
            "- Cada pregunta DEBE tener EXACTAMENTE 4 opciones\n"
            "- Solo UNA opción es correcta\n"
            "- El campo 'correct_index' DEBE ser un número entero (0, 1, 2 o 3)\n"
            "- El campo 'concept' DEBE indicar qué concepto evalúa la pregunta\n"
            "- Todas las respuestas en español\n"
            "- Preguntas claras y concisas\n\n"
            "Formato JSON EXACTO (array de objetos):\n"
            "[\n"
            "  {\n"
            '    "question": "Texto de la pregunta",\n'
            '    "options": ["Opción A", "Opción B", "Opción C", "Opción D"],\n'
            '    "correct_index": 0,\n'
            '    "concept": "nombre del concepto"\n'
            "  }\n"
            "]\n\n"
            "Responde directamente sin pensar en voz alta. "
            "Salida SOLO el array JSON, sin cercas de markdown, sin texto extra."
        ),
        "user": (
            f"Tema: {topic}\n"
            f"Lección: {lesson.get('title', '')}\n"
            f"Puntos clave: {', '.join(lesson.get('bullets', []))}\n"
            f"Conceptos a evaluar: {', '.join(concepts[:3])}\n"
            f"{mistake_context}"
            "Genera 3 preguntas de opción múltiple en formato JSON."
        ),
    }


def build_chat_prompt(message: str, context: dict) -> dict:
    """Build a prompt for tutor chat with student memory."""
    parts = []
    if context.get("topic"):
        parts.append(f"Estudiante está aprendiendo: {context['topic']}")
    if context.get("weak_concepts"):
        parts.append(f"Áreas débiles: {', '.join(context['weak_concepts'])}")
    if context.get("recent_mistakes"):
        parts.append(
            f"Errores recientes: {[m.get('error_description', '') for m in context['recent_mistakes'][:3]]}"
        )
    if context.get("streak"):
        parts.append(f"Racha de estudio: {context['streak']} días")

    student_context = "\n".join(parts) if parts else "Sin contexto previo disponible."

    return {
        "system": (
            "Eres un tutor paciente y alentador. "
            "Responde la pregunta del estudiante claramente. "
            "Referencia su historial de aprendizaje cuando sea relevante. "
            "Mantén las respuestas concisas pero útiles. "
            "Responde siempre en español. "
            "Responde directamente sin pensar en voz alta."
        ),
        "user": (
            f"Contexto del estudiante:\n{student_context}\n\n"
            f"El estudiante pregunta: {message}"
        ),
    }


def build_suggestions_prompt(user_memory: dict, topics_completed: list[str]) -> dict:
    """Build a prompt for smart suggestions based on user history."""
    memory_str = ""
    if user_memory.get("interests"):
        memory_str += f"Intereses del estudiante: {', '.join(user_memory['interests'])}\n"
    if user_memory.get("weak_areas"):
        memory_str += f"Áreas débiles: {', '.join(user_memory['weak_areas'])}\n"
    if user_memory.get("topics_studied"):
        memory_str += f"Temas ya estudiados: {', '.join(user_memory['topics_studied'])}\n"
    if user_memory.get("learning_style"):
        memory_str += f"Estilo de aprendizaje: {user_memory['learning_style']}\n"
    if topics_completed:
        memory_str += f"Temas completados: {', '.join(topics_completed)}\n"

    if not memory_str:
        memory_str = "Sin historial previo. Sugiere temas fundamentales."

    return {
        "system": (
            "Eres un asesor de estudios inteligente. Sugiere exactamente 3 temas de estudio "
            "personalizados basándote en el historial del estudiante.\n\n"
            "REGLAS:\n"
            "- NO sugieras temas ya estudiados\n"
            "- Prioriza áreas débiles del estudiante\n"
            "- Incluye temas que conecten con sus intereses\n"
            "- Cada sugerencia DEBE tener exactamente 1-2 palabras\n"
            "- Ejemplos: 'Ética', 'Lógica Formal', 'Epistemología', 'Estética'\n\n"
            "Formato JSON: array de exactamente 3 cadenas cortas.\n"
            "Responde directamente sin pensar en voz alta. "
            "Responde SOLO en español. "
            "Salida SOLO el array JSON, sin cercas de markdown, sin texto extra."
        ),
        "user": (
            f"Historial del estudiante:\n{memory_str}\n"
            "Sugiere 3 nuevos temas de estudio como array JSON de cadenas cortas."
        ),
    }
