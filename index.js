require('dotenv').config();
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');


const sessionName = process.env.SESSION_NAME || 'axelbot';
const port = process.env.PORT || 3000;


const client = new Client({
    authStrategy: new LocalAuth({ clientId: sessionName }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu'
        ]
    }
});


client.on('qr', qr => {
    console.log("📲 Escanea este QR para conectar WhatsApp:");
    qrcode.generate(qr, { small: true });
});


client.on('ready', () => {
    console.log("✅ Cliente conectado a WhatsApp en el puerto:", port);
});


client.on('message', async msg => {
    const numero = msg.from.replace("@c.us", "");
    const mensaje = msg.body ? msg.body.trim() : "";

    if (!mensaje) {
        console.warn(`⚠️ Mensaje vacío recibido de ${numero}, ignorado.`);
        return;
    }

    console.log(`📨 Mensaje recibido de ${numero}: "${mensaje}"`);

    try {
        const respuesta = await axios.post(
            'http://localhost:5000/respuesta',
            { mensaje, numero },
            { timeout: 5000 } 
        );

        if (respuesta.data) {
            await msg.reply(respuesta.data);
            console.log(`📤 Respuesta enviada a ${numero}: "${respuesta.data}"`);
        } else {
            console.warn(`⚠️ Backend no devolvió respuesta para ${numero}`);
            await msg.reply("⚠️ No recibí respuesta del servidor.");
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


process.on('unhandledRejection', (reason, promise) => {
    console.error("❌ Error no manejado:", reason);
});

process.on('uncaughtException', err => {
    console.error("❌ Excepción no capturada:", err);
});


client.initialize();







