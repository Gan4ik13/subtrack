// Запасной вариант прокси: Koyeb (koyeb.app доступен из РФ без VPN).
// Деплой: Dockerfile + git; всегда живой процесс (нет лимита времени ответа, в отличие от Netlify Functions).
const http = require('http');

const UPSTREAM = 'https://subtrack-api-jszq.onrender.com';
const PORT = process.env.PORT || 8080;

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
};

const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, CORS);
    return res.end();
  }
  const target = UPSTREAM + req.url;
  const chunks = [];
  req.on('data', (c) => chunks.push(c));
  req.on('end', async () => {
    const headers = { ...req.headers };
    delete headers.host;
    delete headers.origin;
    delete headers.referer;
    try {
      const resp = await fetch(target, {
        method: req.method,
        headers,
        body: ['GET', 'HEAD'].includes(req.method) ? undefined : Buffer.concat(chunks),
        redirect: 'follow',
      });
      const out = { ...CORS };
      resp.headers.forEach((v, k) => {
        if (k !== 'content-encoding' && k !== 'transfer-encoding') out[k] = v;
      });
      res.writeHead(resp.status, out);
      const buf = Buffer.from(await resp.arrayBuffer());
      res.end(buf);
    } catch (e) {
      res.writeHead(502, { ...CORS, 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ detail: 'proxy error: ' + e.message }));
    }
  });
  req.on('error', () => { res.writeHead(400); res.end(); });
});

server.listen(PORT, () => console.log('proxy on :' + PORT));
