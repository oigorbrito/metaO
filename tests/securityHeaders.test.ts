import express from 'express';
import http from 'http';

import { isSafeCliOptionValue, isSafeCliPositionalId } from '../src/lib/cliSafety';
import { securityHeaders } from '../src/lib/httpSecurity';

async function main() {
  const safeIds = ['quickstart-accepted', 'runtime_1', 'mission:2026.09'];
  for (const id of safeIds) {
    if (!isSafeCliPositionalId(id)) {
      throw new Error(`Expected safe CLI positional id: ${id}`);
    }
  }
  const unsafeIds = ['', '--db', '-h', 'bad\nvalue', 'bad\rvalue', 'x'.repeat(513)];
  for (const id of unsafeIds) {
    if (isSafeCliPositionalId(id)) {
      throw new Error(`Expected unsafe CLI positional id to be rejected: ${JSON.stringify(id)}`);
    }
  }

  const safeOptionValues = ['Operator quarantine via web console', 'Valid reason 123', 'a'.repeat(512)];
  for (const val of safeOptionValues) {
    if (!isSafeCliOptionValue(val)) {
      throw new Error(`Expected safe CLI option value: ${val}`);
    }
  }
  const unsafeOptionValues = ['', '--flag', '-r', 'bad\nvalue', 'bad\rvalue', 123, 'x'.repeat(513)];
  for (const val of unsafeOptionValues) {
    if (isSafeCliOptionValue(val)) {
      throw new Error(`Expected unsafe CLI option value to be rejected: ${JSON.stringify(val)}`);
    }
  }

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
