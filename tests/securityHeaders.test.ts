import express from 'express';
import http from 'http';

import { securityHeaders } from '../src/lib/httpSecurity';

async function main() {
  const previousNodeEnv = process.env.NODE_ENV;
  process.env.NODE_ENV = 'production';
  const app = express();
  app.use(securityHeaders);
  app.get('/healthz', (_req, res) => res.status(200).send('OK'));

  const server = http.createServer(app);
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));

  try {
    const address = server.address();
    if (!address || typeof address === 'string') {
      throw new Error('Failed to obtain test server address');
    }

    const response = await new Promise<http.IncomingMessage>((resolve, reject) => {
      http
        .get(
          {
            hostname: '127.0.0.1',
            port: address.port,
            path: '/healthz',
          },
          resolve,
        )
        .on('error', reject);
    });

    if (response.statusCode !== 200) {
      throw new Error(`Expected 200, received ${response.statusCode}`);
    }

    const expected: Record<string, string> = {
      'x-content-type-options': 'nosniff',
      'x-frame-options': 'DENY',
      'x-xss-protection': '0',
      'referrer-policy': 'strict-origin-when-cross-origin',
      'permissions-policy': 'camera=(), microphone=(), geolocation=()',
      'content-security-policy':
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
    };

    for (const [name, value] of Object.entries(expected)) {
      if (response.headers[name] !== value) {
        throw new Error(
          `Header ${name} expected ${JSON.stringify(value)}, received ${JSON.stringify(
            response.headers[name],
          )}`,
        );
      }
    }
    if (response.headers['strict-transport-security'] !== undefined) {
      throw new Error(
        'HSTS must be owned by the TLS-terminating deployment layer, not the local HTTP server',
      );
    }
  } finally {
    if (previousNodeEnv === undefined) {
      delete process.env.NODE_ENV;
    } else {
      process.env.NODE_ENV = previousNodeEnv;
    }
    await new Promise<void>((resolve, reject) =>
      server.close((error) => (error ? reject(error) : resolve())),
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
