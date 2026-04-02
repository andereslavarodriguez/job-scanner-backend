import urllib.request
import urllib.error
import json
import asyncio
import re
import os
from dotenv import load_dotenv

load_dotenv()

def _ejecutar_groq_api(prompt, modelo="openai/gpt-oss-120b", json_mode=True):
    url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("\n[-] ERROR: Python dice que la API Key es 'None'. No está leyendo el archivo .env.")
    else:
        print(f"\n[+] API Key detectada en memoria. Empieza por: {api_key[:8]}...")
    
    payload = {
        "model": modelo, 
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    # Interruptor dinámico: Solo forzamos JSON si el agente lo necesita
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
        
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data)
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {api_key}')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
        
        with urllib.request.urlopen(req) as response:
            resultado = json.loads(response.read().decode('utf-8'))
            
            # --- EL CHIVATO MAESTRO PARA TODOS LOS AGENTES ---
            if 'usage' in resultado:
                entrada = resultado['usage'].get('prompt_tokens', 0)
                salida = resultado['usage'].get('completion_tokens', 0)
                total = resultado['usage'].get('total_tokens', 0)
                print(f"\n[📊 TOKENS | {modelo}] Leyó: {entrada} | Escribió: {salida} | Total: {total}")
            # -------------------------------------------------
            
            return resultado['choices'][0]['message']['content'].strip()
            
    except urllib.error.HTTPError as e:
        error_details = e.read().decode('utf-8')
        print(f"\n[-] GROQ ESTÁ ENFADADO POR ESTO: {error_details}")
        return ""
    except Exception as e:
        print(f"Error conectando con la API de Groq: {e}")
        return ""


async def evaluar_oferta(texto_oferta, perfil_usuario):
    prompt = f"""
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
    
    # Modelo asignado: El Cerebro Gigante (Analítica)
    respuesta_raw = await asyncio.to_thread(_ejecutar_groq_api, prompt, "openai/gpt-oss-120b", True)
    
    match = re.search(r'\{.*\}', respuesta_raw, re.DOTALL)
    if match:
        return match.group(0)
    else:
        return '{"afinidad": 0, "puntos_a_favor": [], "puntos_en_contra": ["Error: IA no devolvió formato JSON"]}'


def sintetizar_cv_bruto(texto_bruto):
    prompt = f"""
    You are a talent acquisition expert in charge of structuring and cleaning raw resume data.
    
    RAW RESUME TEXT:
    {texto_bruto}
    
    STRICT INSTRUCTIONS:
    1. Your goal is to restructure the information and clean the format, NOT to summarize it excessively. You must preserve the hard data.
    2. LANGUAGE REQUIREMENT: Detect the language of the "RAW RESUME TEXT". Your final structured text MUST be written in that EXACT SAME LANGUAGE. Do not translate it.
    3. CONTACT DATA: Keep intact at the beginning of the document the contact details, links, and locations present in the original text.
    4. WORK EXPERIENCE: It is mandatory to extract and list each block of experience detailing the exact job title, the company, and the chronological duration of the experience. Do not omit job positions.
    5. SKILLS AND TRAINING: Group the technologies, key tools, and academic degrees clearly and directly.
    6. Write the final result in the first person, maintaining a professional tone, structured in clearly differentiated sections to facilitate its reading.
    7. Return ONLY the final structured text. Do not use JSON format, only plain text.
    """
    
    # Modelo asignado: El Extractor Preciso (Apagamos el JSON mode)
    resultado = _ejecutar_groq_api(prompt, "llama-3.3-70b-versatile", False)
    
    if not resultado:
        return texto_bruto
    return resultado


async def generar_respuesta_campo(contexto_campo, perfil_usuario, texto_oferta=""):
    prompt = f"""
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
    
    # <-- CAMBIO: Devolvemos el poder de redacción al modelo 70B
    respuesta_raw = await asyncio.to_thread(_ejecutar_groq_api, prompt, "llama-3.3-70b-versatile", True)
    
    match = re.search(r'\{.*\}', respuesta_raw, re.DOTALL)
    if match:
        try:
            datos = json.loads(match.group(0))
            return datos.get("respuesta_generada", "INCOMPLETO")
        except:
            return "Error procesando el JSON de Groq"
    else:
        return "Error: Groq no devolvió formato JSON"