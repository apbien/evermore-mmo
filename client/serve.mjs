#!/usr/bin/env node
/** Dev server for the Hearthmere client. `npm run serve` then open :8080. */
import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PORT = process.env.PORT || 8080;
const MIME = {
  '.html':'text/html', '.js':'text/javascript', '.mjs':'text/javascript',
  '.json':'application/json', '.gltf':'model/gltf+json', '.glb':'model/gltf-binary',
  '.bin':'application/octet-stream', '.png':'image/png', '.jpg':'image/jpeg',
};

http.createServer((req, res) => {
  let rel = decodeURIComponent(req.url.split('?')[0]);
  if (rel === '/' ) rel = '/client/index.html';
  let file;
  if (rel.startsWith('/vendor/addons/')) {
    file = path.join(REPO, 'node_modules/three/examples/jsm', rel.slice('/vendor/addons/'.length));
  } else if (rel.startsWith('/vendor/')) {
    file = path.join(REPO, 'node_modules/three/build', rel.slice('/vendor/'.length));
  } else {
    file = path.join(REPO, rel.replace(/^\/+/, ''));
  }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end('404 ' + rel); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(data);
  });
}).listen(PORT, () => console.log(`Hearthmere client → http://localhost:${PORT}`));
