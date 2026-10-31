// Cloudflare Worker — прокси к бэкенду SubPing (Render).
// Нужен, потому что onrender.com и *.vercel.app недоступны из РФ без VPN,
// а сеть Cloudflare доступна. Запрос идёт: клиент (РФ) → CF Worker → Render (США).
//
// Деплой (без CLI):
//   1. https://workers.cloudflare.com → «Create a Worker» → Deploy.
//   2. «Edit code», вставить этот файл целиком, Replace Worker, Deploy.
//   3. Скопировать URL вида https://subping-api.<name>.workers.dev
//   4. Отдать URL — будет прописан в API_BASES фронта (frontend/app.html).
//
// Деплой через API (если есть токен): см. DEPLOY.md.

const UPSTREAM = 'https://subtrack-api-jszq.onrender.com';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
};

export default {
  async fetch(request) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: CORS });
    }
    const url = new URL(request.url);
    const target = UPSTREAM + url.pathname + url.search;
    const headers = {};
    for (const [key, val] of request.headers.entries()) {
      const k = key.toLowerCase();
      if (k === 'host' || k === 'origin' || k === 'referer' || k === 'cf-connecting-ip') continue;
      headers[key] = val;
    }
    let body = undefined;
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      body = await request.arrayBuffer();
    }
    try {
      const resp = await fetch(target, { method: request.method, headers, body, redirect: 'follow' });
      const outHeaders = {};
      resp.headers.forEach((v, k) => {
        if (k === 'content-encoding' || k === 'transfer-encoding') return;
        outHeaders[k] = v;
      });
      Object.assign(outHeaders, CORS);
      return new Response(resp.body, { status: resp.status, headers: outHeaders });
    } catch (e) {
      return Response.json({ detail: 'proxy error: ' + e.message }, { status: 502, headers: CORS });
    }
  },
};
