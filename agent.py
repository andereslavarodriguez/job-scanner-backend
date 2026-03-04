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
    Eres un evaluador de perfiles profesionales. Analiza la compatibilidad de forma rigurosa y objetiva.
    
    PERFIL DEL CANDIDATO:
    {perfil_usuario}
    
    TEXTO DE LA OFERTA:
    {texto_oferta}
    
    INSTRUCCIONES DE EVALUACIÓN:
    1. Analiza los requisitos, la experiencia, el nivel del cargo y las condiciones.
    2. Aplica penalizaciones severas si hay evidencia de sobrecualificación.
    3. Asegúrate de que los puntos a favor y en contra se basan estrictamente en el texto proporcionado.
    4. PUNTUACIÓN DE AFINIDAD: Calcula la afinidad estrictamente como un NÚMERO ENTERO del 0 al 100 (donde 100 es el encaje perfecto).
    5. TONO Y REGISTRO: Dirígete al usuario de forma directa en segunda persona del singular. Redacta el razonamiento y las listas hablándole directamente a quien lee, evitando referirte a él en tercera persona.
    6. EXTRACCIÓN DE DATOS: Identifica el título del puesto y el nombre de la empresa basándote en el texto de la oferta. Si alguno no aparece de forma explícita, escribe "No especificado".
    
    Responde ÚNICAMENTE con un JSON válido que siga esta estructura exacta:
    {{
      "puesto": "string",
      "empresa": "string",
      "razonamiento_interno": "Escribe aquí un párrafo detallando tu proceso lógico al comparar ambos textos. Explica qué coincide, qué falta y si existe alguna discrepancia grave.",
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
    api_key = os.getenv("GROQ_API_KEY") 
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    prompt = f"""
    Eres un experto en selección de talento. Tu tarea es analizar el siguiente texto desordenado extraído de un PDF y sintetizarlo en un perfil profesional claro y estructurado.
    
    TEXTO BRUTO DEL CV:
    {texto_bruto}
    
    INSTRUCCIONES UNIVERSALES:
    1. Extrae y unifica la información vital: rol principal, años de experiencia, habilidades clave, herramientas y nivel educativo.
    2. Elimina caracteres extraños, saltos de línea rotos, columnas descolocadas y datos irrelevantes (como direcciones físicas o aficiones).
    3. Redacta el resultado como un resumen profesional cohesionado en primera persona, fácil de leer y directo al grano.
    4. Devuelve ÚNICAMENTE el texto final sintetizado. No incluyas saludos, introducciones, ni confirmaciones.
    """
    
    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2 # Temperatura baja para que sea preciso y no invente nada
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {api_key}')
        
        with urllib.request.urlopen(req) as response:
            resultado = json.loads(response.read().decode('utf-8'))
            return resultado['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error en el Agente Sintetizador: {e}")
        # Si falla la IA, devolvemos el texto bruto original por seguridad
        return texto_bruto