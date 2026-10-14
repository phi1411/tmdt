import { preview } from 'vite';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
const server = await preview({ root, preview: { host: '127.0.0.1', port: 5174, strictPort: true,
  proxy: { '/api': { target: 'http://127.0.0.1:5002', changeOrigin: true } } } });
server.printUrls();
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => server.httpServer.close(() => process.exit(0)));
