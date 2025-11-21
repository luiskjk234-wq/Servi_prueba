require('dotenv').config();
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

const sessionName = process.env.SESSION_NAME || 'axelbot';
const backendUrl = process.env.BACKEND_URL || 'http://localhost:5000/respuesta';

// Ruta al binario de Chromium descargado por Puppeteer
const chromiumPath = '/root/.cache/puppeteer/chrome/linux-142.0.7444.175/chrome-linux64/chrome';

// Guardamos el momento de inicio para filtrar mensajes antiguos
let startTime = Date.now();

// Set para evitar duplicados
const processedMessages = new Set();

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
  startTime = Date.now(); // actualizamos el tiempo exacto de conexión
});

// Mensajes entrantes
client.on('message', async msg => {
  // 🚫 Ignorar mensajes recibidos antes de la conexión
  const msgTime = msg.timestamp * 1000; // convertir a milisegundos
  if (msgTime < startTime) {
    console.log(`⏳ Mensaje antiguo ignorado de ${msg.from}`);
    return;
  }

  // 🚫 Ignorar mensajes duplicados
  if (processedMessages.has(msg.id._serialized)) {
    console.log(`🔁 Mensaje duplicado ignorado de ${msg.from}`);
    return;
  }
  processedMessages.add(msg.id._serialized);

  // 🚫 Ignorar mensajes de grupos
  if (msg.from.endsWith('@g.us')) {
    console.log("🚫 Mensaje ignorado en grupo:", msg.from);
    return;
  }

  // 🚫 Ignorar mensajes de estados/broadcast
  if (msg.from.endsWith('@broadcast') || msg.from === 'status@broadcast') {
    console.log("🚫 Mensaje ignorado en estados/broadcast:", msg.from);
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
    } else {
      // Respuesta amigable si el backend no devuelve nada
      await msg.reply("🙇‍♂️ Lo sentimos, en este momento estás hablando con el asistente conversacional de Luis.");
      console.log(`ℹ️ Mensaje fuera de flujo respondido a ${numero}`);
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













