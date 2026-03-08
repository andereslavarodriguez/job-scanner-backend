import urllib.request
import urllib.error  # <-- Añadimos esto para poder leer la mente de Groq
import json
import asyncio
import re
import os
from dotenv import load_dotenv

# Cargamos las variables ocultas del sistema [cite: 2025-12-30]
load_dotenv()

def _ejecutar_groq_api(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.getenv("GROQ_API_KEY")
    
    # --- CHIVATO DE DIAGNÓSTICO ---
    if not api_key:
        print("\n[-] ERROR: Python dice que la API Key es 'None'. No está leyendo el archivo .env.")
    else:
        print(f"\n[+] API Key detectada en memoria. Empieza por: {api_key[:8]}...")
    # ------------------------------
    
    payload = {
        # Actualizamos al modelo más moderno por si el anterior caducó
        "model": "llama-3.3-70b-versatile", 
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1, # Subimos de 0.0 a 0.1 (a algunas APIs les da error el cero absoluto)
        "response_format": {"type": "json_object"} 
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {api_key}')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        
        with urllib.request.urlopen(req) as response:
            resultado = json.loads(response.read().decode('utf-8'))
            return resultado['choices'][0]['message']['content']
            
    # --- AQUÍ ATRAPAMOS EL ERROR EXACTO DE GROQ ---
    except urllib.error.HTTPError as e:
        error_details = e.read().decode('utf-8')
        print(f"\n[-] GROQ ESTÁ ENFADADO POR ESTO: {error_details}")
        return ""
    except Exception as e:
        print(f"Error conectando con la API de Groq: {e}")
        return ""
    
async def evaluar_oferta(texto_oferta, perfil_usuario):
    prompt = f"""
    Eres un evaluador riguroso de perfiles profesionales. Tu objetivo es calcular la compatibilidad exacta entre un candidato y una oferta de empleo utilizando un sistema de puntuación matemático, estricto y objetivo.
    
    PERFIL DEL CANDIDATO:
    {perfil_usuario}
    
    TEXTO DE LA OFERTA:
    {texto_oferta}
    
    SISTEMA DE PUNTUACIÓN (Total: 100 puntos):
    Para calcular la afinidad, evalúa estas 4 categorías genéricas de forma estricta:
    1. Requisitos Técnicos y Conocimientos (0-35 puntos): ¿Posee las habilidades duras, herramientas o conocimientos teóricos clave que exige la oferta?
    2. Experiencia y Nivel (0-30 puntos): ¿Coinciden los años de experiencia y el nivel de responsabilidad exigido? Resta puntos por falta de experiencia o por sobrecualificación evidente.
    3. Formación y Habilidades Transversales (0-20 puntos): ¿Cumple con las titulaciones, certificaciones, idiomas y competencias interpersonales requeridas?
    4. Condiciones y Logística (0-15 puntos): ¿Encaja en el modelo de trabajo (remoto/presencial), ubicación y disponibilidad descrita en la oferta?

    REGLAS DE PENALIZACIÓN (Red flags):
    - Si al candidato le falta un requisito catalogado en la oferta como "imprescindible", "excluyente" o "mandatory" (por ejemplo, un idioma obligatorio o un permiso de trabajo), la puntuación total de afinidad NUNCA debe superar los 40 puntos, independientemente de lo bien que encaje en el resto.

    INSTRUCCIONES DE REDACCIÓN:
    - COHERENCIA OBLIGATORIA: Los "puntos_a_favor" y "puntos_en_contra" deben reflejar y justificar exactamente las pérdidas y ganancias de puntos de la rúbrica.
    - TONO Y REGISTRO: Dirígete al usuario de forma directa en segunda persona del singular ("tienes", "te falta").
    - EXTRACCIÓN DE DATOS: Identifica el título del puesto y el nombre de la empresa. Si no aparecen explícitamente, escribe "No especificado".
    
    Responde ÚNICAMENTE con un JSON válido que siga esta estructura exacta:
    {{
      "puesto": "string",
      "empresa": "string",
      "razonamiento_interno": "Realiza aquí el desglose de la puntuación obtenida en cada una de las 4 categorías, suma el total y explica brevemente la lógica de las penalizaciones aplicadas.",
      "afinidad": 0,
      "puntos_a_favor": ["string"],
      "puntos_en_contra": ["string"]
    }}
    """
    
    respuesta_raw = await asyncio.to_thread(_ejecutar_groq_api, prompt)
    
    match = re.search(r'\{.*\}', respuesta_raw, re.DOTALL)
    if match:
        return match.group(0)
    else:
        return '{"afinidad": 0, "puntos_a_favor": [], "puntos_en_contra": ["Error: IA no devolvió formato JSON"]}'



def sintetizar_cv_bruto(texto_bruto):
    import urllib.request, urllib.error, json, os
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.getenv("GROQ_API_KEY") 
    
    prompt = f"""
    Eres un experto en selección de talento. Analiza este texto extraído de un currículum desordenado y sintetízalo en un perfil profesional claro y estructurado.
    
    TEXTO BRUTO DEL CV:
    {texto_bruto}
    
    INSTRUCCIONES UNIVERSALES:
    1. Extrae y unifica la información vital de manera genérica y objetiva.
    2. Elimina caracteres extraños, saltos de línea rotos y datos irrelevantes.
    3. Redacta el resultado como un resumen profesional en primera persona, fácil de leer y directo.
    4. Devuelve ÚNICAMENTE el texto final sintetizado. No uses formato JSON, solo texto plano.
    """
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
        # IMPORTANTE: Eliminamos el "response_format" porque aquí queremos texto normal
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {api_key}')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        
        with urllib.request.urlopen(req) as response:
            resultado = json.loads(response.read().decode('utf-8'))
            return resultado['choices'][0]['message']['content'].strip()
            
    except urllib.error.HTTPError as e:
        # Ahora sí, si Groq se enfada, leeremos su mensaje exacto en Render
        error_details = e.read().decode('utf-8')
        print(f"\n[-] GROQ RECHAZÓ LA PETICIÓN 400: {error_details}")
        return texto_bruto
    except Exception as e:
        print(f"\n[-] ERROR LOCAL AL SINTETIZAR: {e}")
        return texto_bruto