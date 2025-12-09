from flask import Flask, request, jsonify
import re
import unicodedata
from datetime import datetime
import mysql.connector

app = Flask(__name__)

ADMIN = "219954569855190"
LOG = "log.txt"

# Conexión a MySQL
db = mysql.connector.connect(
    host="localhost",
    user="axelbot_user",
    password="LuisKjk345@#",
    database="axelbot"
)

# Horarios disponibles (8:00 a.m. – 9:00 p.m. cada 30 min)
HORAS_DISPONIBLES = [
    f"{h}:{m:02d} {'a.m.' if h < 12 else 'p.m.'}"
    for h in range(8, 21) for m in (0, 30)
]

# Servicios válidos con alias
SERVICIOS_VALIDOS = {
    "corte+barba": "Corte + barba",
    "cb": "Corte + barba",
    "barba": "Corte + barba",
    "barb": "Corte + barba",

    "corte fade": "Corte Fade",
    "cortef": "Corte Fade",
    "fade": "Corte Fade",
    "cf": "Corte Fade",

    "corte": "Corte",
    "cejas": "Diseño de cejas",
    "escolar": "Recortes escolares"
}

# ------------------- UTILIDADES -------------------

def quitar_acentos(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def normalizar_hora(hora_raw):
    if not hora_raw:
        return None
    h = hora_raw.lower().strip()
    h = h.replace("a. m.", "am").replace("p. m.", "pm")
    h = h.replace("a.m.", "am").replace("p.m.", "pm")
    h = h.replace(" ", "").replace(".", "").replace(":", "").replace("-", "")

    match = re.match(r"^(\d{1,2})(\d{2})(a|p)m$", h)
    if match:
        hh, mm = int(match.group(1)), int(match.group(2))
        sufijo = "a.m." if match.group(3) == "a" else "p.m."
        if 0 <= hh <= 12 and 0 <= mm < 60:
            return f"{hh}:{mm:02d} {sufijo}"

    match = re.match(r"^(\d{1,2})(a|p)m$", h)
    if match:
        hh = int(match.group(1))
        sufijo = "a.m." if match.group(2) == "a" else "p.m."
        return f"{hh}:00 {sufijo}"

    match = re.match(r"^([01]?\d|2[0-3])$", h)
    if match:
        hh = int(match.group(1))
        sufijo = "a.m." if hh < 12 else "p.m."
        hh = hh if 1 <= hh <= 12 else hh - 12 if hh > 12 else 12
        return f"{hh}:00 {sufijo}"

    match = re.match(r"^([01]?\d|2[0-3])([0-5]\d)$", h)
    if match:
        hh, mm = int(match.group(1)), int(match.group(2))
        sufijo = "a.m." if hh < 12 else "p.m."
        hh = hh if 1 <= hh <= 12 else hh - 12 if hh > 12 else 12
        return f"{hh}:{mm:02d} {sufijo}"

    for h_disp in HORAS_DISPONIBLES:
        h_flex = h_disp.replace(".", "").replace(" ", "").replace(":", "")
        if h == h_flex:
            return h_disp

    return None

def interpretar_cita(mensaje):
    mensaje = mensaje.lower().replace(";", ",").replace("|", ",").strip()
    partes = [p.strip() for p in mensaje.split(",")] if "," in mensaje else mensaje.split()

    nombre, hora, servicio = None, None, None

    for parte in partes:
        if not parte:
            continue

        h = normalizar_hora(parte)
        if h and not hora:
            hora = h
            continue

        if parte in SERVICIOS_VALIDOS:
            servicio = SERVICIOS_VALIDOS[parte]
            continue

        for clave in sorted(SERVICIOS_VALIDOS.keys(), key=len, reverse=True):
            if clave in parte:
                servicio = SERVICIOS_VALIDOS[clave]
                break

        if not hora and not any(clave in parte for clave in SERVICIOS_VALIDOS):
            nombre = (nombre + " " + parte.title()) if nombre else parte.title()

    return nombre, hora, servicio if servicio else "Corte"

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

# ------------------- ENDPOINT PRINCIPAL -------------------

@app.route('/respuesta', methods=['POST'])
def responder():
    data = request.get_json() or {}
    mensaje = data.get('mensaje', '').strip()
    mensaje_limpio = mensaje.lower()
    mensaje_sin_acentos = quitar_acentos(mensaje_limpio)

    numero_crudo = data.get('numero', '')
    numero_limpio = re.sub(r'[^0-9]', '', numero_crudo)

    print("📨 Mensaje recibido:", mensaje)
    print("📞 Número crudo:", numero_crudo)
    print("📞 Número limpio:", numero_limpio)

    if not mensaje:
        respuesta = "🤖 Escribe algo para que pueda ayudarte."
        registrar_log(numero_limpio, mensaje, respuesta)
        return jsonify(respuesta)

    if numero_limpio == ADMIN:
        if mensaje_sin_acentos.strip().startswith("cancelar") or mensaje_sin_acentos in [
            "ver citas", "ver agenda", "ver citas de hoy",
            "limpiar citas", "borrar citas", "cancelar todas",
            "ver estadisticas", "ver estadísticas"
        ]:
            respuesta = procesar_comando_admin(mensaje_sin_acentos)
            registrar_log(numero_limpio, mensaje, respuesta)
            return jsonify(respuesta)

    nombre, hora, servicio = interpretar_cita(mensaje)
    print("🧠 Interpretado:", f"nombre={nombre}", f"hora={hora}", f"servicio={servicio}")

    if nombre and hora:
        exito = guardar_cita(nombre, hora, servicio, numero_limpio)
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
    else:
        respuesta = responder_menu(mensaje_limpio)

    registrar_log(numero_limpio, mensaje, respuesta)
    return jsonify(respuesta)

# ------------------- FUNCIONES DE CITAS -------------------

def guardar_cita(nombre, hora, servicio, telefono=""):
    fecha = datetime.now().strftime("%Y-%m-%d")
    cursor = db.cursor()
    try:
        sql = """INSERT INTO citas (cliente_nombre, cliente_telefono, servicio, fecha, hora)
                 VALUES (%s, %s, %s, %s, %s)"""
        valores = (nombre, telefono, servicio, fecha, hora)
        cursor.execute(sql, valores)
        db.commit()
        return True
    except mysql.connector.Error as e:
        print("Error al guardar cita:", e)
        return False

def procesar_comando_admin(mensaje):
    if mensaje in ["ver citas", "ver agenda"]:
        return ver_citas()
    if mensaje == "ver citas de hoy":
        return ver_citas(fecha=datetime.now().strftime("%Y-%m-%d"))
    if mensaje in ["limpiar citas", "borrar citas"]:
        return limpiar_citas()
    if mensaje == "cancelar todas":
        return cancelar_todas()
    if mensaje in ["ver estadisticas", "ver estadísticas"]:
        return estadisticas()
    if mensaje.startswith("cancelar"):
        return cancelar_cita(mensaje)
    return responder_menu(mensaje)


def ver_citas(fecha=None):
    cursor = db.cursor(dictionary=True)
    if fecha:
        cursor.execute("SELECT * FROM citas WHERE fecha=%s ORDER BY hora", (fecha,))
    else:
        cursor.execute("SELECT * FROM citas ORDER BY fecha DESC, hora ASC")
    citas = cursor.fetchall()

    if not citas:
        return "📭 No hay citas agendadas aún."

    texto = "📅 *Citas agendadas:*\n"
    for c in citas:
        texto += f"- {c['cliente_nombre']} a las {c['hora']} ({c['fecha']}) — {c['servicio']}\n"
    return texto

def limpiar_citas():
    cursor = db.cursor()
    cursor.execute("DELETE FROM citas")
    db.commit()
    return "🧹 Todas las citas fueron eliminadas."

def cancelar_todas():
    return limpiar_citas()

def cancelar_cita(mensaje):
    partes = mensaje.replace("cancelar", "", 1).split(",")
    if len(partes) < 2:
        return "⚠️ Escribe: *cancelar Nombre, hora*"

    nombre_raw = partes[0].strip()
    hora = normalizar_hora(partes[1].strip())
    fecha = datetime.now().strftime("%Y-%m-%d")

    if not hora:
        return "⚠️ Hora inválida. Ejemplo: *cancelar Luis, 4:30 p.m.*"

    cursor = db.cursor()
    sql = """DELETE FROM citas 
             WHERE cliente_nombre=%s AND hora=%s AND fecha=%s"""
    valores = (nombre_raw, hora, fecha)
    cursor.execute(sql, valores)
    db.commit()

    if cursor.rowcount == 0:
        return "⚠️ No se encontró esa cita para cancelar."
    return f"❌ Cita de *{nombre_raw.title()}* a las *{hora}* cancelada."

def estadisticas():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS total FROM citas")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT fecha, COUNT(*) AS cantidad FROM citas GROUP BY fecha")
    por_fecha = cursor.fetchall()

    cursor.execute("SELECT servicio, COUNT(*) AS cantidad FROM citas GROUP BY servicio")
    por_servicio = cursor.fetchall()

    texto = f"📊 *Estadísticas:*\nTotal de citas: {total}\n"
    for f in por_fecha:
        texto += f"- {f['fecha']}: {f['cantidad']} cita(s)\n"
    if por_servicio:
        texto += "🧾 Por servicio:\n"
        for s in por_servicio:
            texto += f"- {s['servicio']}: {s['cantidad']}\n"
    return texto

# ------------------- MENÚ -------------------

def responder_menu(mensaje):
    if mensaje in ["hola", "buenas", "buenos dias", "buenos días", "buenas tardes", "hey"]:
        return (
            "👋 ¡Hola! Bienvenido a *AxelBot Pro* 💈\n"
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
        "🙇‍♂️ Lo sentimos, en este momento estás hablando con el asistente conversacional de *AxelBot Pro*.\n"
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
    app.run(host="0.0.0.0", port=5000, debug=True)

