from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import json
import PyPDF2
import io

from agent import evaluar_oferta, sintetizar_cv_bruto, generar_respuesta_campo

# ============================================================
# 1. APLICACIÓN
# ============================================================
app = FastAPI(
    title="AI Job Scanner API",
    version="1.4.0",
)

# ============================================================
# 2. CORS
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 3. MODELOS DE DATOS (Pydantic valida automáticamente)
# ============================================================
class DatosEvaluacion(BaseModel):
    perfil: str = Field(..., min_length=10, description="Texto del perfil del candidato")
    descripcion_oferta: str = Field(..., min_length=10, description="Texto de la oferta de trabajo")

class DatosRellenarCampo(BaseModel):
    perfil: str = Field(..., min_length=1)
    contexto: str = Field(..., min_length=1)
    oferta: str = Field(default="")

# ============================================================
# 4. ENDPOINTS
# ============================================================
@app.post("/evaluar")
async def endpoint_evaluar(datos: DatosEvaluacion):
    print(f"\n[+] Petición de evaluación recibida.")
    print(f"--- TEXTO EXTRAÍDO DE LA WEB ---\n{datos.descripcion_oferta[:500]}...\n--------------------------------")

    respuesta_json_string = await evaluar_oferta(datos.descripcion_oferta, datos.perfil)

    try:
        resultado_dict = json.loads(respuesta_json_string)
        print(f"\n[🧠 PENSAMIENTO DE LA IA]: {resultado_dict.get('razonamiento_interno', 'No generó razonamiento')}")
        print(f"[+] Evaluación completada: Afinidad → {resultado_dict.get('afinidad')}%")
        return resultado_dict
    except Exception as e:
        print(f"[-] Error parseando la respuesta de la IA: {e}")
        return {
            "afinidad": 0,
            "puntos_a_favor": [],
            "puntos_en_contra": ["Error de procesamiento en el servidor."],
        }


@app.post("/extraer-cv")
async def extraer_cv(archivo: UploadFile = File(...)):
    if not archivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe ser un PDF.")

    try:
        contenido = await archivo.read()
        lector_pdf = PyPDF2.PdfReader(io.BytesIO(contenido))

        texto_extraido = ""
        for pagina in lector_pdf.pages:
            texto_extraido += pagina.extract_text() + "\n"

        texto_limpio = " ".join(texto_extraido.split())

        if not texto_limpio or len(texto_limpio) < 50:
            raise HTTPException(
                status_code=400,
                detail="No se pudo extraer texto legible del PDF. Puede que sea una imagen escaneada.",
            )

        # sintetizar_cv_bruto ahora es async, await correcto
        texto_optimizado = await sintetizar_cv_bruto(texto_limpio)
        return {"texto_cv": texto_optimizado}

    except HTTPException:
        raise  # Re-lanzamos las HTTPException que hemos creado a propósito
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando el PDF: {str(e)}")


@app.post("/rellenar_campo")
async def rellenar_campo(datos: DatosRellenarCampo):
    print(f"\n[+] Autorrellenado solicitado para el campo: '{datos.contexto}'")

    texto_final = await generar_respuesta_campo(datos.contexto, datos.perfil, datos.oferta)

    print(f"[+] Respuesta generada: {texto_final}")
    return {"respuesta": texto_final}