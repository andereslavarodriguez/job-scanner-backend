from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import evaluar_oferta
import json

# Aquí es donde definimos 'app', lo que te estaba dando el error
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DatosEvaluacion(BaseModel):
    perfil: str
    descripcion_oferta: str

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