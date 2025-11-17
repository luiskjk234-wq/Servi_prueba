
# AxelBot Premium 💈🤖

Un bot de WhatsApp diseñado para **barberías, negocios locales y servicios profesionales** que quieren automatizar su agenda y atención al cliente de forma **rápida, confiable y 24/7**.

---

## 🚀 ¿Qué hace AxelBot Premium?
- 📲 Conecta tu número de WhatsApp y responde automáticamente a tus clientes.  
- 📅 Agenda citas en segundos con nombre, hora y servicio.  
- 💈 Muestra menús interactivos: servicios, promociones, horarios y ubicación.  
- 🧾 Genera estadísticas y reportes de citas.  
- 🔒 Mantiene la sesión activa (sin necesidad de escanear QR cada vez).  
- ☁️ Funciona en Railway/Fly.io con hosting estable 24/7.  

## 📂 Archivos principales
- `index.js` → Bot en Node.js (WhatsApp).  
- `app.py` → Backend Flask (agenda y lógica).  
- `citas.json` → Base de datos simple para pruebas.  
- `Dockerfile` → Configuración lista para Railway.  
- `requirements.txt` → Dependencias de Python.  

---

## ⚙️ Variables de entorno necesarias
Configura en Railway o tu servidor:

- `SESSION_NAME` → Nombre de la sesión de WhatsApp.  
- `PORT` → Puerto de ejecución (ej. 3000).  
- `BACKEND_URL` → URL del backend Flask (ej. `http://backend:5000/respuesta`).  
- `PUPPETEER_EXECUTABLE_PATH` → Ruta de Chromium (ej. `/usr/bin/chromium` en Docker).  

## 🛠️ Instalación rápida
1. Clona el repositorio:
   git clone https://github.com/tuusuario/axelbot-premium.git
   cd axelbot-premium

2. Instala dependencias:
   npm install
   pip install -r requirements.txt

3. Configura el archivo .env:
   SESSION_NAME=axelbot
   PORT=3000
   BACKEND_URL=http://localhost:5000/respuesta
   PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

4. Inicia el backend Flask:
   python app.py

5. Inicia el bot de WhatsApp:
   npm start

## 💎 Beneficios para tu negocio
- Ahorra tiempo: tus clientes reservan sin llamadas ni mensajes manuales.
- Imagen profesional: un bot premium que responde rápido y con estilo.
- Escalable: funciona para barberías, clínicas, restaurantes y cualquier negocio.
- Soporte exclusivo: instalación y configuración inicial incluida.

## 💰 Paquete Premium
Por $120 USD recibes:
- Bot WhatsApp + Backend Flask listos para producción.
- Configuración en Railway/Fly.io con hosting estable.
- Documentación clara y soporte inicial.
- Personalización de nombre, servicios y promociones.

## 📞 Contacto
📲 +58 4126717861  
¿Quieres tu bot premium? Escríbenos y recibe tu demo exclusiva de 2–3 días antes de la instalación completa.

## ⚠️ Uso Responsable

AxelBot Premium utiliza **whatsapp-web.js** para conectarse a tu cuenta de WhatsApp.  
Este sistema está diseñado para la **automatización responsable de citas y atención al cliente**.

- 🚫 No debe usarse para envío masivo de mensajes ni prácticas de spam.  
- 🚫 El uso indebido puede ocasionar bloqueos por parte de WhatsApp.  
- ✅ Nosotros garantizamos la instalación y funcionamiento correcto del bot.  
- ✅ El cliente es responsable de mantener un uso adecuado y dentro de las políticas de WhatsApp.  

👉 Con AxelBot Premium tendrás un asistente confiable y profesional, siempre que se utilice de manera responsable.













