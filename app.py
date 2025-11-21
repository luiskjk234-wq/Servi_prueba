from flask import Flask, request, jsonify
import json
import re
from datetime import datetime

app = Flask(__name__)

ADMIN = "584126717861"
ARCHIVO_CITAS = "citas.json"
LOG = "log.txt"

# Horarios disponibles (8:00 a.m. – 9:00 p.m. cada 30 min)
HORAS_DISPONIBLES = [
    f"{h}:{m:02d} {'a.m.' if h < 12 else 'p.m.'}"
    for h in range(8, 21) for m in (0, 30)
]

# Servicios válidos con alias
SERVICIOS_VALIDOS = {
    "corte": "Corte",
    "fade": "Corte Fade",
    "barba": "Corte + barba",
    "cejas": "Diseño de cejas",
    "escolar": "Recortes escolares",
    "cf": "Corte Fade",
    "cb": "Corte + barba",
    "corte fade": "Corte Fade",
    "corte+barba": "Corte + barba",
    "cortef": "Corte Fade",
    "barb": "Corte + barba"
}

# ------------------- UTILIDADES -------------------

def validar_archivo_citas():
    """Garantiza que citas.json siempre exista y sea válido."""
    try:
        with open(ARCHIVO_CITAS, "r", encoding="utf-8") as f:
            contenido = f.read().strip()
            if not contenido:
                raise ValueError("Archivo vacío")
            json.loads(contenido)
    except:
        with open(ARCHIVO_CITAS, "w", encoding="utf-8") as f:
            json.dump([], f)
        print("⚠️ Archivo de citas reiniciado por corrupción o vacío.")

def normalizar_hora(hora_raw):
    """Acepta múltiples formatos de hora y devuelve estándar."""
    if not hora_raw:
        return None
    h = hora_raw.lower().strip()
    h = h.replace("a. m.", "am").replace("p. m.", "pm")
    h = h.replace("a.m.", "am").replace("p.m.", "pm")
    h = h.replace(" ", "").replace(".", "").replace(":", "").replace("-", "")

    # Ej: 430pm → 4:30 p.m.
    match = re.match(r"^(\d{1,2})(\d{2})(a|p)m$", h)
    if match:
        hh, mm = int(match.group(1)), int(match.group(2))
        sufijo = "a.m." if match.group(3) == "a" else "p.m."
        if 0 <= hh <= 12 and 0 <= mm < 60:
            return f"{hh}:{mm:02d} {sufijo}"

    # Ej: 4pm → 4:00 p.m.
    match = re.match(r"^(\d{1,2})(a|p)m$", h)
    if match:
        hh = int(match.group(1))
        sufijo = "a.m." if match.group(2) == "a" else "p.m."
        return f"{hh}:00 {sufijo}"

    # Ej: 16 → 4:00 p.m.
    match = re.match(r"^([01]?\d|2[0-3])$", h)
    if match:
        hh = int(match.group(1))
        sufijo = "a.m." if hh < 12 else "p.m."
        hh = hh if 1 <= hh <= 12 else hh - 12 if hh > 12 else 12
        return f"{hh}:00 {sufijo}"

    # Ej: 1630 → 4:30 p.m.
    match = re.match(r"^([01]?\d|2[0-3])([0-5]\d)$", h)
    if match:
        hh, mm = int(match.group(1)), int(match.group(2))
        sufijo = "a.m." if hh < 12 else "p.m."
        hh = hh if 1 <= hh <= 12 else hh - 12 if hh > 12 else 12
        return f"{hh}:{mm:02d} {sufijo}"

    # Buscar coincidencia flexible en HORAS_DISPONIBLES
    for h_disp in HORAS_DISPONIBLES:
        h_flex = h_disp.replace(".", "").replace(" ", "").replace(":", "")
        if h == h_flex:
            return h_disp

    return None

def interpretar_cita(mensaje):
    mensaje = mensaje.lower().replace(";", ",").replace("|", ",").strip()
    partes = [p.strip() for p in mensaje.split(",")] if "," in mensaje else mensaje.split()

    nombre, hora, servicio = None, None, "Corte"

    for parte in partes:
        if not parte:
            continue
        # Si aún no tenemos hora, intentamos parsear
        h = normalizar_hora(parte)
        if h and not hora:
            hora = h
            continue
        # Si es un servicio válido
        if parte in SERVICIOS_VALIDOS:
            servicio = SERVICIOS_VALIDOS[parte]
            continue
        else:
            for clave in SERVICIOS_VALIDOS:
                if clave in parte:
                    servicio = SERVICIOS_VALIDOS[clave]
                    break
        # Si no es hora ni servicio, lo tratamos como nombre (acumulamos palabras)
        if not hora and not any(clave in parte for clave in SERVICIOS_VALIDOS):
            nombre = (nombre + " " + parte.title()) if nombre else parte.title()

    return nombre, hora, servicio if servicio else "Corte"
    
def sugerir_horas(hora):
    """Sugiere horas cercanas si la solicitada está ocupada."""
    idx = [i for i, h in enumerate(HORAS_DISPONIBLES) if h == hora]
    if not idx:
        return []
    i = idx[0]
    sugerencias = []
    for offset in [-1, 1, 2]:
        j = i + offset
        if 0 <= j < len(HORAS_DISPONIBLES):
            sugerencias.append(HORAS_DISPONIBLES[j])
    return sugerencias

# ------------------- ENDPOINT PRINCIPAL -------------------

@app.route('/respuesta', methods=['POST'])
def responder():
    validar_archivo_citas()
    data = request.get_json() or {}
    mensaje = data.get('mensaje', '').strip()
    numero = data.get('numero', '').replace("@c.us", "").replace("+", "")
    mensaje_limpio = mensaje.lower()

    print("📨 Mensaje recibido:", mensaje)
    print("📞 Número recibido:", numero)

    if not mensaje:
        respuesta = "🤖 Escribe algo para que pueda ayudarte."
        registrar_log(numero, mensaje, respuesta)
        return jsonify(respuesta)

    nombre, hora, servicio = interpretar_cita(mensaje)
    print("🧠 Interpretado:", f"nombre={nombre}", f"hora={hora}", f"servicio={servicio}")

    if nombre and hora:
        exito = guardar_cita(nombre, hora, servicio)
        if exito:
            respuesta = (
                f"✅ ¡Listo, {nombre}! Tu cita fue agendada a las *{hora}* 💈\n"
                f"🧾 Servicio: *{servicio}*"
            )
        else:
            sugerencias = sugerir_horas(hora)
            texto_sugerencias = "\n".join([f"- {h}" for h in sugerencias]) or "No hay horarios alternativos."
            respuesta = (
                f"⚠️ La hora *{hora}* ya está ocupada.\n"
                f"¿Qué tal estas opciones?\n{texto_sugerencias}"
            )
    elif numero == ADMIN:
        respuesta = procesar_comando_admin(mensaje_limpio)
    else:
        respuesta = responder_menu(mensaje_limpio)

    registrar_log(numero, mensaje, respuesta)
    return jsonify(respuesta)

# ------------------- FUNCIONES DE CITAS -------------------

def guardar_cita(nombre, hora, servicio):
    fecha = datetime.now().strftime("%Y-%m-%d")
    nueva_cita = {"nombre": nombre, "hora": hora, "fecha": fecha, "servicio": servicio}
    print("💾 Guardando cita:", nueva_cita)

    try:
        with open(ARCHIVO_CITAS, "r", encoding="utf-8") as f:
            citas = json.load(f)
    except:
        citas = []

    if any(c["fecha"] == fecha and c["hora"] == hora and c["nombre"] == nombre for c in citas):
        print("⚠️ Cita ya existe, no se agenda.")
        return False

    citas.append(nueva_cita)
    with open(ARCHIVO_CITAS, "w", encoding="utf-8") as f:
        json.dump(citas, f, indent=2, ensure_ascii=False)
    return True

# ------------------- ADMIN -------------------

def procesar_comando_admin(mensaje):
    if mensaje in ["ver citas", "ver agenda"]:
        return ver_citas()
    if mensaje == "ver citas de hoy":
        return ver_citas(fecha=datetime.now().strftime("%Y-%m-%d"))
    if mensaje in ["limpiar citas", "borrar citas"]:
        return limpiar_citas()
    if mensaje == "cancelar todas":
        return cancelar_todas()
    if mensaje == "ver estadísticas":
        return estadisticas()
    if mensaje.startswith("cancelar"):
        return cancelar_cita(mensaje)
    return responder_menu(mensaje)

def ver_citas(fecha=None):
    try:
        with open(ARCHIVO_CITAS, "r", encoding="utf-8") as f:
            citas = json.load(f)
        if not citas:
            return "📭 No hay citas agendadas aún."
        texto = "📅 *Citas agendadas:*\n"
        for c in citas:
            if fecha and c["fecha"] != fecha:
                continue
            texto += f"- {c['nombre']} a las {c['hora']} ({c['fecha']}) — {c['servicio']}\n"
        return texto if texto != "📅 *Citas agendadas:*\n" else "📭 No hay citas para hoy."
    except Exception as e:
        return f"⚠️ Error al leer la agenda: {e}"

def limpiar_citas():
    with open(ARCHIVO_CITAS, "w", encoding="utf-8") as f:
        json.dump([], f)
    return "🧹 Citas eliminadas correctamente."

def cancelar_todas():
    validar_archivo_citas()
    return limpiar_citas()

def cancelar_cita(mensaje):
    partes = mensaje.replace("cancelar", "", 1).split(",")
    if len(partes) < 2:
        return "⚠️ Escribe: *cancelar Nombre, hora*"
    nombre = partes[0].strip().title()
    hora = normalizar_hora(partes[1].strip())
    fecha = datetime.now().strftime("%Y-%m-%d")

    if not hora:
        return "⚠️ Hora inválida. Ejemplo: *cancelar Luis, 4:30 p.m.*"

    try:
        with open(ARCHIVO_CITAS, "r", encoding="utf-8") as f:
            citas = json.load(f)
    except Exception as e:
        print("⚠️ Error al leer citas.json:", e)
        return "⚠️ No se pudo acceder a la agenda."

    nuevas = [c for c in citas if not (c["nombre"] == nombre and c["hora"] == hora and c["fecha"] == fecha)]
    if len(nuevas) == len(citas):
        return "⚠️ No se encontró esa cita para cancelar."

    with open(ARCHIVO_CITAS, "w", encoding="utf-8") as f:
        json.dump(nuevas, f, indent=2, ensure_ascii=False)
    return f"❌ Cita de *{nombre}* a las *{hora}* cancelada."

def estadisticas():
    try:
        with open(ARCHIVO_CITAS, "r", encoding="utf-8") as f:
            citas = json.load(f)
        total = len(citas)
        por_fecha = {}
        por_servicio = {}
        for c in citas:
            por_fecha[c["fecha"]] = por_fecha.get(c["fecha"], 0) + 1
            por_servicio[c["servicio"]] = por_servicio.get(c["servicio"], 0) + 1

        texto = f"📊 *Estadísticas:*\nTotal de citas: {total}\n"
        for fecha, cantidad in por_fecha.items():
            texto += f"- {fecha}: {cantidad} cita(s)\n"
        if por_servicio:
            texto += "🧾 Por servicio:\n"
            for serv, qty in por_servicio.items():
                texto += f"- {serv}: {qty}\n"
        return texto
    except:
        return "⚠️ No se pudo calcular estadísticas."

# ------------------- MENÚ -------------------

def responder_menu(mensaje):
    if mensaje in ["hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "hey"]:
        return (
            "👋 ¡Hola! Bienvenido a *Barbería El Estilo* 💈\n"
            "¿En qué puedo ayudarte hoy?\n\n"
            "📋 Escribe una opción:\n"
            "1️⃣ Ver servicios\n"
            "2️⃣ Reservar cita\n"
            "3️⃣ Promociones\n"
            "4️⃣ Horarios\n"
            "5️⃣ Ubicación\n\n"
            "También puedes escribir: *Nombre, hora, servicio* para reservar directo."
        )
    elif mensaje in ["1", "servicios"]:
        return (
            "💈 *Nuestros servicios:*\n"
            "- Corte Fade\n- Corte + barba\n- Diseño de cejas\n- Recortes escolares\n\n"
            "Para reservar: *Nombre, hora, servicio*\nEjemplo: *Luis Pérez, 4:30 p.m., Corte + barba*"
        )
    elif mensaje in ["2", "reservar", "cita"]:
        return (
            "📆 Para reservar tu cita, escribe:\n"
            "*Nombre, hora, servicio*\nEjemplo: *Luis Pérez, 4:30 p.m., Corte + barba*"
        )
    elif mensaje in ["3", "promociones", "promo"]:
        return (
            "🎉 *Promoción del día:*\nCorte + barba por *$150 MXN* 💸\nVálido hasta las 7:00 p.m."
        )
    elif mensaje in ["4", "horarios", "horario"]:
        return "🕒 *Horario:* Lunes a Domingo, 8:00 a.m. a 9:00 p.m. cada 30 min."
    elif mensaje in ["5", "ubicacion", "ubicación", "donde estan", "dónde están"]:
        return "📍 *Ubicación:* Calz. de Tlalpan 5063, La Joya, CDMX. Frente a Converse 🚇"
    return (
    "🙇‍♂️ Lo sentimos, en este momento estás hablando con el asistente conversacional de *Luis*.\n"
    "Puedes usar el menú para reservar o consultar:\n"
    "1️⃣ Servicios\n2️⃣ Reservar\n3️⃣ Promociones\n4️⃣ Horarios\n5️⃣ Ubicación\n\n"
    "O si prefieres, escribe directamente: *Nombre, hora, servicio* para agendar tu cita."
)
# ------------------- LOG -------------------

def registrar_log(numero, mensaje, respuesta):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | {numero} | {mensaje} | {respuesta}\n")
    except:
        print("⚠️ No se pudo escribir en el log.")

# ------------------- MAIN -------------------

if __name__ == '__main__':
    # En producción, usa Gunicorn:
    # pm2 start "gunicorn -w 2 -b 127.0.0.1:5000 app:app" --name Axelbot-Backend
    app.run(debug=True)


