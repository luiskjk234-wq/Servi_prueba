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
    const mensaje = msg.body.trim();

    console.log(`📨 Mensaje recibido de ${numero}: ${mensaje}`);

    try {
        const respuesta = await axios.post('http://localhost:5000/respuesta', {
            mensaje: mensaje,
            numero: numero
        });

        if (respuesta.data) {
            msg.reply(respuesta.data);
            console.log(`📤 Respuesta enviada a ${numero}`);
        }
    } catch (error) {
        console.error("❌ Error al enviar al backend:", error.message);
        msg.reply("⚠️ Hubo un error al procesar tu mensaje.");
    }
});


client.on('auth_failure', msg => {
    console.error("❌ Fallo de autenticación:", msg);
});

client.on('disconnected', reason => {
    console.warn("⚠️ Cliente desconectado:", reason);
});

client.initialize();





