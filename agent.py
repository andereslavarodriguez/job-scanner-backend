import urllib.request
import urllib.error
import json
import asyncio
import re
import os
from dotenv import load_dotenv

load_dotenv()

def _ejecutar_groq_api(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("\n[-] ERROR: API Key not found.")
    
    payload = {
        "model": "llama-3.3-70b-versatile", 
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
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
            
    except urllib.error.HTTPError as e:
        error_details = e.read().decode('utf-8')
        print(f"\n[-] GROQ ERROR: {error_details}")
        return ""
    except Exception as e:
        print(f"Error connecting to Groq: {e}")
        return ""

async def evaluar_oferta(texto_oferta, perfil_usuario):
    prompt = f"""
    You are a rigorous professional profile evaluator. Your goal is to calculate the exact compatibility between a candidate and a job offer using a mathematical, strict, and objective scoring system.
    
    CANDIDATE PROFILE:
    {perfil_usuario}
    
    JOB OFFER TEXT:
    {texto_oferta}
    
    SCORING SYSTEM (Total: 100 points):
    Evaluate these 4 generic categories strictly to calculate affinity:
    1. Technical Requirements and Knowledge (0-35 points): Does the candidate have the hard skills, tools, or theoretical knowledge required?
    2. Experience and Level (0-30 points): Do the years of experience and level of responsibility match? Subtract points for lack of experience or obvious overqualification.
    3. Training and Transversal Skills (0-20 points): Does the candidate meet the degrees, certifications, languages, and interpersonal skills?
    4. Conditions and Logistics (0-15 points): Does the candidate fit the work model (remote/on-site), location, and availability?

    PENALIZATION RULES (Red flags):
    - If the candidate lacks a requirement labeled as "imprescindible", "excluyente", or "mandatory", the total affinity score MUST NOT exceed 40 points, regardless of other matches.

    WRITING INSTRUCTIONS:
    1. LANGUAGE DETECTION: Detect the language of the "JOB OFFER TEXT". Your final evaluation (puntos_a_favor, puntos_en_contra, razonamiento_interno) MUST be written in that EXACT SAME LANGUAGE.
    2. COHERENCE: "puntos_a_favor" and "puntos_en_contra" must justify the score gains or losses based on the rubric.
    3. TONE: Address the user directly in the second person singular (e.g., "tienes", "te falta" if Spanish; "you have", "you lack" if English).
    4. DATA EXTRACTION: Identify the job title and company name. If not explicitly found, write "No especificado".
    
    Respond ONLY with a valid JSON following this exact structure:
    {{
      "puesto": "string",
      "empresa": "string",
      "razonamiento_interno": "string",
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
    You are a talent acquisition expert tasked with structuring and cleaning raw resume data.
    
    RAW RESUME TEXT:
    {texto_bruto}
    
    STRICT INSTRUCTIONS:
    1. Your goal is to restructure the information and clean the format, NOT to over-summarize it. You must preserve hard data.
    2. LANGUAGE DETECTION: Detect the language of the "RAW RESUME TEXT". Your final synthesized profile MUST be written in that EXACT SAME LANGUAGE. Do not translate the CV.
    3. CONTACT DATA: Keep contact details, links, and locations from the original text intact at the beginning of the document.
    4. WORK EXPERIENCE: You must extract and list every experience block detailing the exact job title, company, and chronological duration. Do not omit any jobs.
    5. SKILLS AND EDUCATION: Group technologies, key tools, and academic degrees clearly and directly.
    6. Write the final result in the first person, maintaining a professional tone, structured in clearly differentiated sections.
    7. Return ONLY the final structured text. Do not use JSON format, only plain text.
    """
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
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
        error_details = e.read().decode('utf-8')
        print(f"\n[-] GROQ RECHAZÓ LA PETICIÓN 400: {error_details}")
        return texto_bruto
    except Exception as e:
        print(f"\n[-] ERROR LOCAL AL SINTETIZAR: {e}")
        return texto_bruto
    
async def generar_respuesta_campo(contexto_campo, perfil_usuario, texto_oferta=""):
    prompt = f"""
    You are an AI assistant specialized in filling out job application forms automatically.
    
    CANDIDATE PROFILE:
    {perfil_usuario}
    
    JOB OFFER CONTEXT:
    {texto_oferta}
    
    FIELD TO FILL OUT (Target Question):
    "{contexto_campo}"
    
    STRICT INSTRUCTIONS:
    1. ABSOLUTE LANGUAGE RULE: The language of your response MUST EXACTLY MATCH the language of the "FIELD TO FILL OUT". You MUST IGNORE the language of the CANDIDATE PROFILE and JOB OFFER CONTEXT when choosing your output language. 
       - If "FIELD TO FILL OUT" is in English -> You MUST write the response in English.
       - If "FIELD TO FILL OUT" is in Spanish -> You MUST write the response in Spanish.
    2. Answer ONLY the specific question asked in the "FIELD TO FILL OUT". Do not invent information.
    3. FIRST PERSON: Use the first person singular ("I", "Yo", etc.) maintaining a professional tone.
    4. ALIGNMENT: Adapt the profile information to fit the job offer context, but answer ONLY the field's question.
    5. MISSING INFO: If the requested information is absolutely nowhere to be found in the profile, your output must be exactly the word: INCOMPLETO.
    6. Provide NO explanations, NO conversational filler, and NO introductory phrases.
    
    Respond ONLY with a valid JSON:
    {{
      "respuesta_generada": "string"
    }}
    """
    
    import json
    import re
    import asyncio
    
    respuesta_raw = await asyncio.to_thread(_ejecutar_groq_api, prompt)
    match = re.search(r'\{.*\}', respuesta_raw, re.DOTALL)
    if match:
        try:
            datos = json.loads(match.group(0))
            return datos.get("respuesta_generada", "INCOMPLETO")
        except:
            return "Error processing JSON"
    return "Error: No JSON returned"