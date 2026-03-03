import asyncio
import json
import time
from agent import evaluar_oferta

# 10 Perfiles Genéricos variados
perfiles = {
    "P1_Junior_Data": "1 año exp. Data entry y SQL básico. Busca rol formativo, remoto.",
    "P2_Mid_Python": "3 años exp. Python y APIs. Busca rol híbrido, buen sueldo.",
    "P3_Senior_ML": "8 años exp. Machine Learning y Arquitectura. Bilingüe. Busca liderazgo.",
    "P4_Lead_Tech": "12 años exp. Gestión de equipos de 20+ personas. CTO o Director.",
    "P5_Junior_Marketing": "Recién graduado en Marketing Digital. Creador de contenido. Prácticas.",
    "P6_Mid_Ventas": "4 años exp. B2B software sales. Acostumbrado a trabajar por objetivos.",
    "P7_Soporte_IT": "2 años exp. Helpdesk y resolución de incidencias. Turnos de noche.",
    "P8_Senior_DevOps": "6 años exp. Docker, Kubernetes, AWS. 100% remoto indispensable.",
    "P9_Junior_HR": "6 meses exp. criba curricular. Nivel alto de inglés.",
    "P10_Mid_Finanzas": "5 años exp. contabilidad y Excel avanzado. Presencial."
}

# 10 Ofertas Genéricas variadas
ofertas = {
    "O1_Beca_Datos": "Beca formativa en análisis de datos. 6 meses, jornada parcial. Remoto.",
    "O2_Backend_Python": "Buscamos desarrollador Python con +3 años exp. Modelo híbrido.",
    "O3_Director_IA": "Líder para dpto. de Inteligencia Artificial. +5 años gestionando equipos. Bilingüe.",
    "O4_CTO_Startup": "Buscamos líder técnico global (+10 años) para escalar producto desde cero.",
    "O5_Especialista_SEO": "Se busca perfil mid (+3 años) para estrategia SEO técnica.",
    "O6_Account_Executive": "Ventas B2B de software. Se requiere exp. demostrable cerrando deals.",
    "O7_Soporte_L1": "Técnico de soporte primer nivel. Horario intensivo de mañana.",
    "O8_Cloud_Architect": "Arquitecto AWS/K8s. Posición 100% remota. Urgente.",
    "O9_Recruiter_Tech": "Buscamos IT Recruiter senior (+4 años exp). Inglés fluido.",
    "O10_Analista_Riesgos": "Analista financiero junior (+1 año exp). 100% Presencial."
}

async def ejecutar_100_tests():
    print(f"🚀 Iniciando Matriz de 100 Pruebas (10 Perfiles x 10 Ofertas)")
    print("⏳ Por las cuotas gratuitas de Groq, esto tomará aprox. 3-4 minutos...\n")
    
    total_evaluaciones = 0
    
    for id_perfil, texto_perfil in perfiles.items():
        for id_oferta, texto_oferta in ofertas.items():
            total_evaluaciones += 1
            print(f"[{total_evaluaciones}/100] Cruzando {id_perfil} con {id_oferta}...")
            
            respuesta_json = await evaluar_oferta(texto_oferta, texto_perfil)
            
            try:
                datos = json.loads(respuesta_json)
                afinidad = datos.get("afinidad", 0)
                
                # Visualización por colores
                if afinidad >= 80:
                    color = "\033[92m" # Verde (Match perfecto)
                elif afinidad >= 40:
                    color = "\033[93m" # Amarillo (Dudas)
                else:
                    color = "\033[91m" # Rojo (Descarte)
                    
                reset = "\033[0m"
                print(f"   => Afinidad: {color}{afinidad}%{reset}")
                
            except Exception as e:
                print(f"   => \033[91m[!] Error procesando JSON o fallo de API\033[0m")
                
            # FRENO ANTI-BLOQUEO: 2 segundos de pausa entre peticiones
            await asyncio.sleep(2)

if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(ejecutar_100_tests())
    print(f"\n✅ Completado en {round(time.time() - start_time, 1)} segundos.")