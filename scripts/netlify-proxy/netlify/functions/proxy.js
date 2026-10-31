// Netlify Function — прокси к бэкенду SubPing (Render).
// Деплой: scripts/netlify-proxy/deploy.sh (нужен NETLIFY_TOKEN в переменной окружения).
// ВАЖНО: не путать с Cloudflare — здесь egress идёт с инфраструктуры Netlify (AWS),
// поэтому Render (за CF) отвечает штатно, в отличие от CF Worker.

const UPSTREAM = 'https://subtrack-api-jszq.onrender.com';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
};

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: CORS, body: '' };
  }
  // Чистый путь: /api/me, /health, ... (redirect в netlify.toml убирает префикс функции)
  const path = event.path || '/';
  const query = event.rawQuery ? '?' + event.rawQuery : '';
  const target = UPSTREAM + path + query;

  const headers = {};
  for (const [k, v] of Object.entries(event.headers || {})) {
    const key = k.toLowerCase();
    if (['host', 'origin', 'referer', 'x-forwarded-for'].includes(key)) continue;
    headers[key] = v;
  }

  let body;
  if (event.httpMethod !== 'GET' && event.httpMethod !== 'HEAD') {
    body = event.isBase64Encoded ? Buffer.from(event.body, 'base64') : event.body;
  }

  try {
    const resp = await fetch(target, { method: event.httpMethod, headers, body, redirect: 'follow' });
    const outHeaders = {};
    resp.headers.forEach((v, k) => {
      if (k === 'content-encoding' || k === 'transfer-encoding') return;
      outHeaders[k] = v;
    });
    Object.assign(outHeaders, CORS);
    const buf = Buffer.from(await resp.arrayBuffer());
    return {
      statusCode: resp.status,
      headers: outHeaders,
      body: buf.toString('base64'),
      isBase64Encoded: true,
    };
  } catch (e) {
    return {
      statusCode: 502,
      headers: { ...CORS, 'Content-Type': 'application/json' },
      body: JSON.stringify({ detail: 'proxy error: ' + e.message }),
    };
  }
};
