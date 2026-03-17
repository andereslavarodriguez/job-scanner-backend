from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import PyPDF2
import io

# Importamos la nueva función generar_respuesta_campo
from agent import evaluar_oferta, sintetizar_cv_bruto, generar_respuesta_campo 

# 1. CREAMOS LA APLICACIÓN (Los cimientos)
app = FastAPI()

# 2. CONFIGURAMOS CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. MODELOS DE DATOS
class DatosEvaluacion(BaseModel):
    perfil: str
    descripcion_oferta: str

# 4. RUTAS (ENDPOINTS)
@app.post("/evaluar")
async def endpoint_evaluar(datos: DatosEvaluacion):
    print(f"\n[+] Recibida petición de evaluación.")
    print(f"--- TEXTO EXTRAÍDO DE LA WEB ---\n{datos.descripcion_oferta[:500]}...\n--------------------------------")
    
    # Llamamos a tu IA
    respuesta_json_string = await evaluar_oferta(datos.descripcion_oferta, datos.perfil)
    
    try:
        resultado_dict = json.loads(respuesta_json_string)
        print(f"\n[🧠 PENSAMIENTO DE LA IA]: {resultado_dict.get('razonamiento_interno', 'No generó razonamiento')}")
        print(f"[+] Evaluación completada: Afinidad -> {resultado_dict.get('afinidad')}%")
        return resultado_dict
    except Exception as e:
        print(f"[-] Error parseando la respuesta de la IA: {e}")
        return {"afinidad": 0, "puntos_a_favor": [], "puntos_en_contra": ["Error de procesamiento en el servidor local."]}
    
@app.post("/extraer-cv")
async def extraer_cv(archivo: UploadFile = File(...)):
    # Verificamos que sea un PDF
    if not archivo.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF")
    
    try:
        # Leemos el archivo directamente desde la memoria
        contenido = await archivo.read()
        lector_pdf = PyPDF2.PdfReader(io.BytesIO(contenido))
        
        texto_extraido = ""
        # Recorremos todas las páginas del PDF extrayendo el texto
        for pagina in lector_pdf.pages:
            texto_extraido += pagina.extract_text() + "\n"
            
        # Limpiamos los saltos de línea excesivos
        texto_limpio = " ".join(texto_extraido.split())
        
        if not texto_limpio or len(texto_limpio) < 50:
            raise HTTPException(status_code=400, detail="No se pudo extraer texto legible del PDF. Puede que sea una imagen escaneada.")
            
        # Pasamos el texto robótico por nuestro Agente Sintetizador
        texto_optimizado = sintetizar_cv_bruto(texto_limpio)
        
        return {"texto_cv": texto_optimizado}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el PDF: {str(e)}")
    
@app.post("/rellenar_campo")
async def rellenar_campo(request: Request):
    try:
        data = await request.json()
        perfil_usuario = data.get("perfil", "")
        contexto_campo = data.get("contexto", "")
        texto_oferta = data.get("oferta", "") # NUEVO: Atrapamos el contexto de la web
        
        print(f"\n[+] Solicitud de autorrellenado recibida para el campo: {contexto_campo}")
        
        # Pasamos los 3 datos a la IA de Groq
        texto_final = await generar_respuesta_campo(contexto_campo, perfil_usuario, texto_oferta)
        
        print(f"[+] Respuesta generada: {texto_final}")
        return {"respuesta": texto_final}

    except Exception as e:
        print(f"[-] Error en el endpoint rellenar_campo: {str(e)}")
        return {"error": str(e)}