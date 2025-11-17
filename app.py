from flask import Flask, request, jsonify
import json
import re
from datetime import datetime

app = Flask(__name__)

ADMIN = "584126717861"
ARCHIVO_CITAS = "citas.json"
LOG = "log.txt"

HORAS_DISPONIBLES = [
    f"{h}:{m:02d} {'a.m.' if h < 12 else 'p.m.'}"
    for h in range(8, 21) for m in (0, 30)
]

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

def validar_archivo_citas():
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
    if not hora_raw:
        return None
    hora_raw = hora_raw.lower().strip()
    hora_raw = hora_raw.replace("a. m.", "am").replace("p. m.", "pm")
    hora_raw = hora_raw.replace("a.m.", "am").replace("p.m.", "pm")
    hora_raw = hora_raw.replace("a m", "am").replace("p m", "pm")
    hora_raw = hora_raw.replace(" ", "").replace(".", "").replace(":", "").replace(";", "").replace("-", "")

    match = re.match(r"^(\d{1,2})(\d{2})(a|p)m?$", hora_raw)
    if match:
        h = int(match.group(1))
        m = int(match.group(2))
        sufijo = "a.m." if match.group(3) == "a" else "p.m."
        if 0 <= h <= 12 and 0 <= m < 60:
            return f"{h}:{m:02d} {sufijo}"

    match = re.match(r"^(\d{1,2})(a|p)m?$", hora_raw)
    if match:
        h = int(match.group(1))
        sufijo = "a.m." if match.group(2) == "a" else "p.m."
        if 0 <= h <= 12:
            return f"{h}:00 {sufijo}"

    match = re.match(r"^([01]?\d|2[0-3])$", hora_raw)
    if match:
        h = int(match.group(1))
        sufijo = "a.m." if h < 12 else "p.m."
        h = h if 1 <= h <= 12 else h - 12 if h > 12 else 12
        return f"{h}:00 {sufijo}"

    match = re.match(r"^([01]?\d|2[0-3])([0-5]\d)$", hora_raw)
    if match:
        h = int(match.group(1))
        m = int(match.group(2))
        sufijo = "a.m." if h < 12 else "p.m."
        h = h if 1 <= h <= 12 else h - 12 if h > 12 else 12
        return f"{h}:{m:02d} {sufijo}"

    for h in HORAS_DISPONIBLES:
        h_flexible = h.replace(".", "").replace(" ", "").replace(":", "")
        if hora_raw == h_flexible:
            return h

    return None

def interpretar_cita(mensaje):
    mensaje = mensaje.lower().replace(";", ",").replace("|", ",").replace("  ", " ").strip()
    partes = [p.strip() for p in mensaje.split(",")] if "," in mensaje else mensaje.split()

    nombre = None
    hora = None
    servicio = "Corte"

    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        if not nombre and parte.isalpha():
            nombre = parte.title()
        elif not hora:
            h = normalizar_hora(parte)
            if h:
                hora = h
        elif parte in SERVICIOS_VALIDOS:
            servicio = SERVICIOS_VALIDOS[parte]
        elif any(s in parte for s in SERVICIOS_VALIDOS):
            for clave in SERVICIOS_VALIDOS:
                if clave in parte:
                    servicio = SERVICIOS_VALIDOS[clave]

    if nombre and hora:
        return nombre, hora, servicio
    return None, None, None

def sugerir_horas(hora):
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

@app.route('/respuesta', methods=['POST'])
def responder():
    validar_archivo_citas()
    data = request.get_json()
    mensaje = data.get('mensaje', '').strip()
    numero = data.get('numero', '').replace("@c.us", "").replace("+", "")
    mensaje_limpio = mensaje.lower()

    print("📨 Mensaje recibido:", mensaje)
    print("📞 Número recibido:", numero)

    if not mensaje:
        return jsonify("🤖 Escribe algo para que pueda ayudarte.")

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
            texto_sugerencias = "\n".join([f"- {h}" for h in sugerencias])
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

def guardar_cita(nombre, hora, servicio):
    fecha = datetime.now().strftime("%Y-%m-%d")
    nueva_cita = {"nombre": nombre, "hora": hora, "fecha": fecha, "servicio": servicio}
    print("💾 Guardando cita:", nueva_cita)

    try:
        with open(ARCHIVO_CITAS, "r", encoding="utf-8") as f:
            contenido = f.read().strip()
            citas = json.loads(contenido) if contenido else []
    except Exception as e:
        print("⚠️ Error al leer citas.json:", e)
        citas = []

    if any(c["fecha"] == fecha and c["hora"] == hora and c["nombre"] == nombre for c in citas):
        print("⚠️ Cita ya existe, no se agenda.")
        return False

    citas.append(nueva_cita)
    with open(ARCHIVO_CITAS, "w", encoding="utf-8") as f:
        json.dump(citas, f, indent=2, ensure_ascii=False)
    return True

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

    try:
        with open(ARCHIVO_CITAS, "r", encoding="utf-8") as f:
            contenido = f.read().strip()
            citas = json.loads(contenido) if contenido else []
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
        for c in citas:
            por_fecha[c["fecha"]] = por_fecha.get(c["fecha"], 0) + 1
        texto = f"📊 *Estadísticas:*\nTotal de citas: {total}\n"
        for fecha, cantidad in por_fecha.items():
            texto += f"- {fecha}: {cantidad} cita(s)\n"
        return texto
    except:
        return "⚠️ No se pudo calcular estadísticas."

def responder_menu(mensaje):
    if mensaje in ["hola", "buenas", "buenos días", "buenas tardes"]:
        return (
            "👋 ¡Hola! Bienvenido a *Barbería El Estilo* 💈\n"
            "¿En qué puedo ayudarte hoy?\n\n"
            "📋 Escribe una opción:\n"
            "1️⃣ Ver servicios\n"
            "2️⃣ Reservar cita\n"
            "3️⃣ Promociones\n"
            "4️⃣ Horarios\n"
            "5️⃣ Ubicación"
        )
    elif mensaje in ["1", "servicios"]:
        return (
            "💈 *Nuestros servicios:*\n"
            "- Corte Fade\n- Corte + barba\n- Diseño de cejas\n- Recortes escolares\n\n"
            "Escribe: *Tu nombre, hora, servicio*"
        )
    elif mensaje in ["2", "reservar", "cita"]:
        return (
            "📆 Para reservar tu cita, escribe:\n"
            "*Nombre, hora, servicio*\nEjemplo: *Luis, 4:30 p.m., Corte + barba*"
        )
    elif mensaje in ["3", "promociones", "promo"]:
        return (
            "🎉 *Promoción del día:*\nCorte + barba por *$150 MXN* 💸\nVálido hasta las 7:00 p.m."
        )
    elif mensaje in ["4", "horarios", "horario"]:
        return "🕒 *Horario:* Lunes a Domingo, 8:30 a.m. a 9:00 p.m."
    elif mensaje in ["5", "ubicación", "dónde están"]:
        return "📍 *Ubicación:* Calz. de Tlalpan 5063, La Joya, CDMX. Frente a Converse 🚇"
    return (
        "🤖 No entendí tu mensaje. Escribe una opción del menú:\n"
        "1️⃣ Servicios\n2️⃣ Reservar\n3️⃣ Promociones\n4️⃣ Horarios\n5️⃣ Ubicación"
    )

def registrar_log(numero, mensaje, respuesta):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | {numero} | {mensaje} | {respuesta}\n")

if __name__ == '__main__':
    app.run(debug=True)
