require('dotenv').config();
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

const sessionName = process.env.SESSION_NAME || 'axelbot';
const backendUrl = process.env.BACKEND_URL || 'http://localhost:5000/respuesta';

const client = new Client({
  authStrategy: new LocalAuth({ clientId: sessionName, dataPath: './session' }),
  puppeteer: {
    headless: 'new',
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/chromium',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  }
});

client.on('qr', qr => {
  console.log("📲 Escanea este QR para conectar WhatsApp:");
  qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
  console.log("✅ Cliente conectado a WhatsApp");
});

client.on('message', async msg => {
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

client.on('auth_failure', msg => {
  console.error("❌ Fallo de autenticación:", msg);
});

client.on('disconnected', reason => {
  console.warn("⚠️ Cliente desconectado:", reason);
  console.log("🔄 Intentando reconectar...");
  client.initialize();
});

process.on('unhandledRejection', reason => {
  console.error("❌ Error no manejado:", reason);
});

process.on('uncaughtException', err => {
  console.error("❌ Excepción no capturada:", err);
});

client.initialize();









