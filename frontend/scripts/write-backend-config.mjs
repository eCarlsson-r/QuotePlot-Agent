import { writeFile } from 'node:fs/promises';

const backendOrigin = (process.env.QUOTE_PLOT_BACKEND_ORIGIN || '').replace(/\/+$/, '');

if (backendOrigin) {
  const url = new URL(backendOrigin);
  const allowedProtocol = url.protocol === 'https:' ||
    (url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname));
  if (!allowedProtocol || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('QUOTE_PLOT_BACKEND_ORIGIN must be an HTTPS origin (HTTP is allowed for localhost only).');
  }
}

const config = `window.__QUOTE_PLOT_CONFIG__ = ${JSON.stringify({ backendOrigin })};\n`;
await writeFile(new URL('../public/quoteplot-config.js', import.meta.url), config);
