require("dotenv").config();
const TelegramBot = require("node-telegram-bot-api");
const axios = require("axios");
const cheerio = require("cheerio");
const HttpsProxyAgent = require("https-proxy-agent");
const HttpProxyAgent = require("http-proxy-agent");

const bot = new TelegramBot(process.env.BOT_TOKEN, { polling: true });

// 🔁 delay
const delay = (ms) => new Promise(res => setTimeout(res, ms));

// 🌐 proxy storage
let proxyList = [];
let useProxy = false;

// 🎯 random proxy
function getRandomProxy() {
  if (proxyList.length === 0) return null;
  return proxyList[Math.floor(Math.random() * proxyList.length)];
}

// 🔍 fetch data
async function getData(vehicle) {
  try {
    const proxy = useProxy ? getRandomProxy() : null;

    let config = {
      headers: { "User-Agent": "Mozilla/5.0" },
      timeout: 15000
    };

    if (proxy) {
      config.httpAgent = new HttpProxyAgent(proxy);
      config.httpsAgent = new HttpsProxyAgent(proxy);
    }

    const res = await axios.get(`https://vahanx.in/rc-search/${vehicle}`, config);

    const $ = cheerio.load(res.data);

    const owner = $("div:contains('Owner Name')").next().text().trim();
    const phone = $("div:contains('Phone')").next().text().trim();
    const city = $("div:contains('City Name')").next().text().trim();

    return { owner, phone, city };

  } catch (err) {
    console.log("Error:", err.message);
    return null;
  }
}

// 🔁 retry
async function getDataWithRetry(vehicle, retries = 3) {
  for (let i = 0; i < retries; i++) {
    const data = await getData(vehicle);
    if (data) return data;
  }
  return null;
}

// 🚀 START
bot.onText(/\/start/, (msg) => {
  bot.sendMessage(msg.chat.id, `
🤖 *Vehicle Info Bot*

Commands:
➡️ /rc VEHICLE
➡️ /bulk num1,num2
➡️ /proxy PROXY_URL
➡️ /proxies
➡️ /clearproxy
➡️ /proxyon /proxyoff

Example:
👉 /rc BR05H4963
  `, { parse_mode: "Markdown" });
});

// 🚗 SINGLE
bot.onText(/\/rc (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const vehicle = match[1].toUpperCase();

  bot.sendMessage(chatId, "🔍 Checking...");

  const data = await getDataWithRetry(vehicle);

  if (!data) {
    return bot.sendMessage(chatId, "❌ Failed / Blocked");
  }

  bot.sendMessage(chatId, `
🚗 *Vehicle:* ${vehicle}

👤 *Owner:* ${data.owner || "N/A"}
📱 *Mobile:* ${data.phone || "N/A"}
📍 *City:* ${data.city || "N/A"}
  `, { parse_mode: "Markdown" });
});

// ⚡ BULK
bot.onText(/\/bulk (.+)/, async (msg, match) => {
  const chatId = msg.chat.id;
  const vehicles = match[1].split(",");

  bot.sendMessage(chatId, "⚡ Bulk started...");

  for (let v of vehicles) {
    v = v.trim().toUpperCase();

    const data = await getDataWithRetry(v);

    await bot.sendMessage(chatId, `
🚗 ${v}
👤 ${data?.owner || "N/A"}
📱 ${data?.phone || "N/A"}
📍 ${data?.city || "N/A"}
    `);

    await delay(2500);
  }

  bot.sendMessage(chatId, "✅ Bulk done");
});

// ➕ ADD PROXY
bot.onText(/\/proxy (.+)/, (msg, match) => {
  const proxy = match[1].trim();
  proxyList.push(proxy);

  bot.sendMessage(msg.chat.id, `✅ Proxy added`);
});

// 📡 LIST
bot.onText(/\/proxies/, (msg) => {
  if (proxyList.length === 0) {
    return bot.sendMessage(msg.chat.id, "❌ No proxies");
  }
  bot.sendMessage(msg.chat.id, proxyList.join("\n"));
});

// 🗑️ CLEAR
bot.onText(/\/clearproxy/, (msg) => {
  proxyList = [];
  bot.sendMessage(msg.chat.id, "🗑️ All proxies removed");
});

// 🔛 PROXY ON
bot.onText(/\/proxyon/, (msg) => {
  useProxy = true;
  bot.sendMessage(msg.chat.id, "✅ Proxy Enabled");
});

// 🔴 PROXY OFF
bot.onText(/\/proxyoff/, (msg) => {
  useProxy = false;
  bot.sendMessage(msg.chat.id, "❌ Proxy Disabled");
});

// ❌ INVALID
bot.on("message", (msg) => {
  if (!msg.text.startsWith("/")) {
    bot.sendMessage(msg.chat.id, "❌ Use valid command (/rc ...)");
  }
});
