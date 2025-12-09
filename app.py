from flask import Flask, request, jsonify
import re
import unicodedata
from datetime import datetime
import mysql.connector

app = Flask(__name__)

ADMIN = "219954569855190"
LOG = "log.txt"

# Flag de modo demo (True = cualquier horario permitido)
DEMO_MODE = True

# Conexión a MySQL (usa la base de demo)
db = mysql.connector.connect(
    host="localhost",
    user="axelbot_user",
    password="LuisKjk345@#",
    database="axelbot_demo"
)

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
        return f"{hh}:{mm:02d} {sufijo}"

    match = re.match(r"^(\d{1,2})(a|p)m$", h)
    if match:
        hh = int(match.group(1))
        sufijo = "a.m." if match.group(2) == "a" else "p.m."
        return f"{hh}:00 {sufijo}"

    return None

def hora_humana_a_mysql(hhmm_ampm: str) -> str:
    m = re.match(r"^(\d{1,2}):([0-5]\d)\s*(a\.m\.|p\.m\.)$", hhmm_ampm.strip(), re.IGNORECASE)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
    suf = m.group(3).lower()
    if hh == 12:
        hh24 = 0 if suf.startswith("a") else 12
    else:
        hh24 = hh if suf.startswith("a") else hh + 12
    return f"{hh24:02d}:{mm:02d}:00"

def hora_mysql_a_humana(hhmmss: str) -> str:
    hh, mm, _ = hhmmss.split(":")
    hh = int(hh)
    suf = "a.m." if hh < 12 else "p.m."
    hh12 = 12 if hh == 0 else (hh if hh <= 12 else hh - 12)
    return f"{hh12}:{int(mm):02d} {suf}"

# ------------------- ENDPOINT PRINCIPAL -------------------

@app.route('/respuesta', methods=['POST'])
def responder():
    data = request.get_json() or {}
    mensaje = data.get('mensaje', '').strip()
    mensaje_limpio = mensaje.lower()
    mensaje_sin_acentos = quitar_acentos(mensaje_limpio)

    numero_crudo = data.get('numero', '')
    numero_limpio = re.sub(r'[^0-9]', '', numero_crudo)

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

    partes = mensaje.split(",")
    nombre = partes[0].strip().title() if len(partes) > 0 else None
    hora = normalizar_hora(partes[1].strip()) if len(partes) > 1 else None
    servicio = partes[2].strip().title() if len(partes) > 2 else "Corte"

    if nombre and hora:
        exito = guardar_cita(nombre, hora, servicio, numero_limpio)
        if exito:
            respuesta = (
                f"✅ ¡Listo, {nombre}! Tu cita fue agendada a las *{hora}* 💈\n"
                f"🧾 Servicio: *{servicio}*"
            )
        else:
            respuesta = f"⚠️ La hora *{hora}* ya está ocupada."
    else:
        respuesta = responder_menu(mensaje_limpio)

    registrar_log(numero_limpio, mensaje, respuesta)
    return jsonify(respuesta)

# ------------------- FUNCIONES DE CITAS -------------------

def guardar_cita(nombre, hora, servicio, telefono=""):
    fecha = datetime.now().strftime("%Y-%m-%d")
    hora_mysql = hora_humana_a_mysql(hora)
    if not hora_mysql:
        return False

    cursor = db.cursor()
    try:
        sql = """INSERT INTO citas_demo (cliente_nombre, cliente_telefono, servicio, fecha, hora)
                 VALUES (%s, %s, %s, %s, %s)"""
        valores = (nombre, telefono, servicio, fecha, hora_mysql)
        cursor.execute(sql, valores)
        db.commit()
        return True
    except mysql.connector.Error as e:
        if getattr(e, "errno", None) == 1062:  # Duplicate entry
            return False
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
        cursor.execute("SELECT cliente_nombre, servicio, fecha, TIME_FORMAT(hora, '%H:%i:%s') AS hora FROM citas_demo WHERE fecha=%s ORDER BY hora", (fecha,))
    else:
        cursor.execute("SELECT cliente_nombre, servicio, fecha, TIME_FORMAT(hora, '%H:%i:%s') AS hora FROM citas_demo ORDER BY fecha DESC, hora ASC")
    citas = cursor.fetchall()

    if not citas:
        return "📭 No hay citas agendadas aún."

    texto = "📅 *Citas agendadas:*\n"
    for c in citas:
        texto += f"- {c['cliente_nombre']} a las {hora_mysql_a_humana(c['hora'])} ({c['fecha']}) — {c['servicio']}\n"
    return texto

def limpiar_citas():
    cursor = db.cursor()
    cursor.execute("DELETE FROM citas_demo")
    db.commit()
    return "🧹 Todas las citas fueron eliminadas."

def cancelar_todas():
    return limpiar_citas()

def cancelar_cita(mensaje):
    partes = mensaje.replace("cancelar", "", 1).split(",")
    if len(partes) < 2:
        return "⚠️ Escribe: *cancelar Nombre, hora*"

    nombre_raw = partes[0].strip()
    hora_humana = normalizar_hora(partes[1].strip())
    if not hora_humana:
        return "⚠️ Hora inválida. Ejemplo: *cancelar Luis, 4:30 p.m.*"

    hora_mysql = hora_humana_a_mysql(hora_humana)
    fecha = datetime.now().strftime("%Y-%m-%d")

    cursor = db.cursor()
    sql = """DELETE FROM citas_demo 
             WHERE cliente_nombre=%s AND hora=%s AND fecha=%s"""
    valores = (nombre_raw, hora_mysql, fecha)
    cursor.execute(sql, valores)
    db.commit()

    if cursor.rowcount == 0:
        return "⚠️ No se encontró esa cita para cancelar."
    return f"❌ Cita de *{nombre_raw.title()}* a las *{hora_humana}* cancelada."

def estadisticas():
    cursor = db.cursor(dictionary=True)

    # Total de citas
    cursor.execute("SELECT COUNT(*) AS total FROM citas_demo")
    total = cursor.fetchone()["total"]

    # Citas por fecha
    cursor.execute("SELECT fecha, COUNT(*) AS cantidad FROM citas_demo GROUP BY fecha")
    por_fecha = cursor.fetchall()

    # Citas por servicio
    cursor.execute("SELECT servicio, COUNT(*) AS cantidad FROM citas_demo GROUP BY servicio")
    por_servicio = cursor.fetchall()

    # Construir texto
    texto = f"📊 *Estadísticas:*\nTotal de citas: {total}\n"
    for f in por_fecha:
        texto += f"- {f['fecha']}: {f['cantidad']} cita(s)\n"

    if por_servicio and len(por_servicio) > 0:
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
        return "🕒 *Horario:* Lunes a Domingo, cualquier hora disponible (modo demo)."
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

