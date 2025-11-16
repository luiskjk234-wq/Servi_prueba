# AxelBot Premium

Bot de WhatsApp con Puppeteer + whatsapp-web.js y backend Flask.

## 🚀 Cómo funciona
- Escanea un QR para vincular tu número.
- El bot responde mensajes y se conecta al backend Flask.
- El backend maneja la lógica de citas y respuestas.

## 📂 Archivos principales
- `index.js` → Bot en Node.js
- `aplicación.py` → Backend Flask
- `citas.json` → Base de datos simple
- `Dockerfile` → Configuración para Railway

## ⚙️ Variables de entorno
Configura en Railway:
- `SESSION_NAME`
- `PORT`
- `BACKEND_URL`
