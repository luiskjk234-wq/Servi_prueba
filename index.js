require('dotenv').config();
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

const sessionName = process.env.SESSION_NAME || 'axelbot';
const backendUrl = process.env.BACKEND_URL || 'http://localhost:5000/respuesta';

// Ruta al binario de Chromium descargado por Puppeteer
const chromiumPath = '/root/.cache/puppeteer/chrome/linux-142.0.7444.175/chrome-linux64/chrome';

const client = new Client({
  authStrategy: new LocalAuth({ clientId: sessionName, dataPath: './session' }),
  puppeteer: {
    headless: true,
    executablePath: chromiumPath,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--no-first-run',
      '--no-zygote',
      '--single-process',
      '--disable-gpu',
      '--disable-software-rasterizer',
      '--disable-extensions',
      '--disable-background-networking',
      '--disable-sync'
    ]
  }
});

// Evento QR
client.on('qr', qr => {
  console.log("📲 Escanea este QR para conectar WhatsApp:");
  qrcode.generate(qr, { small: true });
});

// Cliente listo
client.on('ready', () => {
  console.log("✅ Cliente conectado a WhatsApp y listo para recibir mensajes");
});

// Mensajes entrantes
client.on('message', async msg => {
  // Ignorar mensajes de grupos
  if (msg.from.endsWith('@g.us')) {
    console.log("🚫 Mensaje ignorado en grupo:", msg.from);
    return;
  }

  const numero = msg.from.replace("@c.us", "");
  const mensaje = msg.body ? msg.body.trim() : "";

  if (!mensaje) return;

  try {
    const { data } = await axios.post(backendUrl, { mensaje, numero });
    if (data) {
      await msg.reply(data);
      console.log(`📤 Respuesta enviada a ${numero}: "${data}"`);
    }
  } catch (error) {
    console.error("❌ Error al enviar al backend:", error.message);
    await msg.reply("⚠️ Hubo un error al procesar tu mensaje.");
  }
});

// Fallo de autenticación
client.on('auth_failure', msg => {
  console.error("❌ Fallo de autenticación:", msg);
});

// Cliente desconectado
client.on('disconnected', reason => {
  console.warn("⚠️ Cliente desconectado:", reason);
  console.log("🔄 La sesión se cerró. Borra ./session si quieres reconectar con otro número.");
});

// Manejo de errores globales
process.on('unhandledRejection', reason => {
  console.error("❌ Error no manejado:", reason);
});

process.on('uncaughtException', err => {
  console.error("❌ Excepción no capturada:", err);
});

// Inicializar cliente
client.initialize();










