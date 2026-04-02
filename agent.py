import httpx
import json
import asyncio
import re
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURACIÓN GLOBAL
# ============================================================
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_INPUT_CHARS = 20_000   # Límite de seguridad para cualquier texto de entrada
MAX_REINTENTOS = 2          # Número de reintentos si Groq falla

# ── Modelos ────────────────────────────────────────────────
# Cada tarea tiene el modelo más adecuado para ella.
# Cambia aquí si quieres probar alternativas sin tocar el resto del código.
MODELO_EVALUACION  = "openai/gpt-oss-120b"        # Razonamiento estricto. Necesita el modelo grande.
MODELO_SINTETIZAR  = "llama-3.1-8b-instant"        # Solo restructura texto. Rápido y con límites altos (500K tokens/día).
MODELO_AUTORELLENO = "llama-3.3-70b-versatile"     # Redacción con criterio. 70B es suficiente y soporta json_mode.

# ============================================================
# PROMPTS (separados de la lógica para facilitar su edición)
# ============================================================
PROMPT_EVALUAR = """
You are a rigorous professional profile evaluator. Your goal is to calculate the exact compatibility between a candidate and a job offer using a mathematical, strict, and objective scoring system.

CANDIDATE PROFILE:
{perfil_usuario}

JOB OFFER TEXT:
{texto_oferta}

SCORING SYSTEM (Total: 100 points):
To calculate affinity, strictly evaluate these 4 generic categories:
1. Technical Requirements and Knowledge (0-35 points): Does the candidate possess the hard skills, tools, or key theoretical knowledge required by the offer?
2. Experience and Level (0-30 points): Do the years of experience and demanded level of responsibility match? Subtract points for lack of experience or obvious overqualification.
3. Training and Transversal Skills (0-20 points): Does the candidate meet the required degrees, certifications, languages, and interpersonal skills?
4. Conditions and Logistics (0-15 points): Does the candidate fit the work model (remote/on-site), location, and availability described in the offer?

PENALIZATION RULES (Red flags):
- If the candidate lacks a requirement cataloged in the offer as strictly mandatory or exclusive, the total affinity score MUST NEVER exceed 40 points, regardless of how well they fit the rest.

WRITING INSTRUCTIONS:
- LANGUAGE REQUIREMENT: Detect the language of the "JOB OFFER TEXT". Your evaluation content MUST be written in that EXACT SAME LANGUAGE. DO NOT translate the JSON keys.
- MANDATORY COHERENCE: The "puntos_a_favor" and "puntos_en_contra" must exactly reflect and justify the points gained and lost from the rubric.
- TONE AND REGISTER: Address the user directly in the second person singular.
- DATA EXTRACTION: Identify the job title and the company name. If they do not explicitly appear, write "No especificado".

Respond ONLY with a valid JSON that follows this exact structure:
{{
  "puesto": "string",
  "empresa": "string",
  "razonamiento_interno": "Perform the breakdown of the score obtained in each of the 4 categories here, sum the total, and briefly explain the logic of the applied penalizations.",
  "afinidad": 0,
  "puntos_a_favor": ["string"],
  "puntos_en_contra": ["string"]
}}
"""

PROMPT_SINTETIZAR_CV = """
You are a talent acquisition expert in charge of structuring and cleaning raw resume data.

RAW RESUME TEXT:
{texto_bruto}

STRICT INSTRUCTIONS:
1. Your goal is to restructure the information and clean the format, NOT to summarize it excessively. You must preserve the hard data.
2. LANGUAGE REQUIREMENT: Detect the language of the "RAW RESUME TEXT". Your final structured text MUST be written in that EXACT SAME LANGUAGE. Do not translate it.
3. CONTACT DATA: Keep intact at the beginning of the document the contact details, links, and locations present in the original text.
4. DYNAMIC STRUCTURE: Organize the content into clearly separated main sections (e.g., Work Experience, Education, Projects, Certifications, etc.) based on whatever exists in the raw text. Do not ignore non-standard sections.
5. STRICT HIERARCHY (CRITICAL TO AVOID MIXING): For sections containing multiple items (like several jobs or several projects), you MUST clearly separate each item:
   - Start each new item on a new line using a bold header format for its title and dates.
   - List the internal details, responsibilities, or technologies of that specific item underneath it using standard bullet points.
   - ALWAYS leave a blank empty line between one item and the next.
6. Write the final result in the first person, maintaining a professional tone.
7. Return ONLY the final structured plain text. Do not use JSON format.
"""

PROMPT_RELLENAR_CAMPO = """
You are an Artificial Intelligence assistant that fills out job application forms invisibly.

CANDIDATE PROFILE:
{perfil_usuario}

JOB OFFER CONTEXT:
{texto_oferta}

FIELD TO FILL OUT:
"{contexto_campo}"

STRICT INSTRUCTIONS:
1. LANGUAGE REQUIREMENT: Detect the language of the "FIELD TO FILL OUT". You MUST generate your EXACT TEXT in that SAME LANGUAGE, regardless of the language of the candidate profile or the job offer.
2. Your only mission is to generate the EXACT TEXT that must be entered into that form box.
3. Analyze the "FIELD TO FILL OUT". If it is a simple piece of data, extract that exact data from the profile and write it without adding anything else.
4. If the field requires development, write a professional, concise response in the first person.
5. STRATEGIC ALIGNMENT: Analyze the "JOB OFFER CONTEXT". Omit profile information that is irrelevant to this generic case and emphasize the skills and experiences that maximize compatibility with the described requirements.
6. If the requested information does not exist in any way in the profile, the response text must be exactly the word: INCOMPLETO.
7. Do not include explanations.

Respond ONLY with a valid JSON that follows this exact structure:
{{
  "respuesta_generada": "string"
}}
"""


# ============================================================
# MOTOR CENTRAL: LLAMADA A GROQ CON HTTPX Y REINTENTOS
# ============================================================
async def _llamar_groq(prompt: str, modelo: str, json_mode: bool = True) -> str:
    """
    Llama a la API de Groq de forma asíncrona.
    Reintenta automáticamente hasta MAX_REINTENTOS veces si hay un error de red o 5xx.
    """
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("\n[-] ERROR: GROQ_API_KEY no encontrada en el archivo .env.")
        return ""

    print(f"\n[+] API Key detectada. Empieza por: {api_key[:8]}...")

    payload = {
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Reintentos con espera exponencial: 1s, 2s
    for intento in range(MAX_REINTENTOS + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(GROQ_URL, json=payload, headers=headers)

            if response.status_code == 200:
                resultado = response.json()

                # Chivato de tokens (igual que tenías)
                if "usage" in resultado:
                    uso = resultado["usage"]
                    print(
                        f"\n[📊 TOKENS | {modelo}] "
                        f"Leyó: {uso.get('prompt_tokens', 0)} | "
                        f"Escribió: {uso.get('completion_tokens', 0)} | "
                        f"Total: {uso.get('total_tokens', 0)}"
                    )

                return resultado["choices"][0]["message"]["content"].strip()

            # Error del servidor (5xx): vale la pena reintentar
            elif response.status_code >= 500:
                print(f"\n[-] Groq devolvió {response.status_code}. Intento {intento + 1}/{MAX_REINTENTOS + 1}.")
                if intento < MAX_REINTENTOS:
                    await asyncio.sleep(2 ** intento)  # 1s, 2s
                else:
                    print(f"\n[-] Groq sigue fallando tras {MAX_REINTENTOS + 1} intentos.")
                    return ""

            # Error del cliente (4xx): no tiene sentido reintentar
            else:
                print(f"\n[-] GROQ ESTÁ ENFADADO: {response.status_code} → {response.text}")
                return ""

        except httpx.TimeoutException:
            print(f"\n[-] Timeout en intento {intento + 1}. Reintentando...")
            if intento < MAX_REINTENTOS:
                await asyncio.sleep(2 ** intento)
            else:
                print("\n[-] Timeout definitivo. Groq no respondió a tiempo.")
                return ""

        except Exception as e:
            print(f"\n[-] Error inesperado conectando con Groq: {e}")
            return ""

    return ""


# ============================================================
# FUNCIONES PÚBLICAS (la lógica de negocio no cambia)
# ============================================================
async def evaluar_oferta(texto_oferta: str, perfil_usuario: str) -> str:
    # Limitamos el tamaño de los inputs para no gastar tokens de más
    texto_oferta = texto_oferta[:MAX_INPUT_CHARS]
    perfil_usuario = perfil_usuario[:MAX_INPUT_CHARS]

    prompt = PROMPT_EVALUAR.format(
        perfil_usuario=perfil_usuario,
        texto_oferta=texto_oferta,
    )

    # Modelo asignado: Evaluación
    respuesta_raw = await _llamar_groq(prompt, MODELO_EVALUACION, json_mode=True)

    match = re.search(r"\{.*\}", respuesta_raw, re.DOTALL)
    if match:
        return match.group(0)
    return '{"afinidad": 0, "puntos_a_favor": [], "puntos_en_contra": ["Error: IA no devolvió formato JSON"]}'


async def sintetizar_cv_bruto(texto_bruto: str) -> str:
    """
    Ahora es async para no bloquear el servidor de FastAPI
    mientras espera la respuesta de Groq.
    """
    texto_bruto = texto_bruto[:MAX_INPUT_CHARS]

    prompt = PROMPT_SINTETIZAR_CV.format(texto_bruto=texto_bruto)

    # Modelo asignado: Sintetizar CV
    resultado = await _llamar_groq(prompt, MODELO_SINTETIZAR, json_mode=False)

    return resultado if resultado else texto_bruto


async def generar_respuesta_campo(
    contexto_campo: str, perfil_usuario: str, texto_oferta: str = ""
) -> str:
    perfil_usuario = perfil_usuario[:MAX_INPUT_CHARS]
    texto_oferta = texto_oferta[:MAX_INPUT_CHARS]

    prompt = PROMPT_RELLENAR_CAMPO.format(
        perfil_usuario=perfil_usuario,
        texto_oferta=texto_oferta,
        contexto_campo=contexto_campo,
    )

    # Modelo asignado: Autorelleno
    respuesta_raw = await _llamar_groq(prompt, MODELO_AUTORELLENO, json_mode=True)

    match = re.search(r"\{.*\}", respuesta_raw, re.DOTALL)
    if match:
        try:
            datos = json.loads(match.group(0))
            return datos.get("respuesta_generada", "INCOMPLETO")
        except Exception:
            return "Error procesando el JSON de Groq"

    return "Error: Groq no devolvió formato JSON"