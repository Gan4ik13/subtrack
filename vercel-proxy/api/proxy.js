const UPSTREAM = 'https://subtrack-api-jszq.onrender.com';

module.exports = async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  const target = UPSTREAM + url.pathname + url.search;

  const headers = {};
  for (const [key, val] of Object.entries(req.headers)) {
    if (['host', 'origin', 'referer'].includes(key)) continue;
    headers[key] = val;
  }

  const init = {
    method: req.method,
    headers,
    redirect: 'follow',
  };

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    init.body = Buffer.concat(chunks);
  }

  try {
    const resp = await fetch(target, init);
    res.status(resp.status);
    resp.headers.forEach((v, k) => {
      if (k === 'content-encoding') return;
      res.setHeader(k, v);
    });
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
    const body = await resp.arrayBuffer();
    res.send(Buffer.from(body));
  } catch (e) {
    res.status(502).json({ detail: 'proxy error: ' + e.message });
  }
};
