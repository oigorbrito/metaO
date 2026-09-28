import http from 'http';
import { createServerApp } from '../server';

async function testSecurityHeaders() {
  console.log('Testing HTTP Security Headers...');
  const app = createServerApp();

  const server = http.createServer(app);
  await new Promise<void>((resolve) => server.listen(0, resolve));

  const address = server.address();
  if (!address || typeof address === 'string') {
    throw new Error('Failed to obtain server address');
  }

  const url = `http://localhost:${address.port}/healthz`;

  try {
    const res = await new Promise<http.IncomingMessage>((resolve, reject) => {
      http.get(url, (response) => resolve(response)).on('error', reject);
    });

    if (res.statusCode !== 200) {
      throw new Error(`Expected status 200, got ${res.statusCode}`);
    }

    const headers = res.headers;
    const requiredHeaders: Record<string, string> = {
      'x-content-type-options': 'nosniff',
      'x-frame-options': 'DENY',
      'x-xss-protection': '0',
      'referrer-policy': 'strict-origin-when-cross-origin',
      'permissions-policy': 'camera=(), microphone=(), geolocation=()',
    };

    for (const [header, expectedValue] of Object.entries(requiredHeaders)) {
      const actualValue = headers[header];
      if (actualValue !== expectedValue) {
        throw new Error(`Header mismatch for ${header}. Expected "${expectedValue}", got "${actualValue}"`);
      }
      console.log(`  ✓ ${header}: ${actualValue}`);
    }

    console.log('All security headers verified successfully!');
  } finally {
    server.close();
  }
}

testSecurityHeaders().catch((err) => {
  console.error('Security headers test failed:', err);
  process.exit(1);
});
