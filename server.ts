import express from 'express';
import path from 'path';
import { execFile } from 'child_process';
import { fileURLToPath } from 'url';

import { securityHeaders } from './src/lib/httpSecurity';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CLI_BIN = process.env.METAO_CLI_BIN || 'metao';
const DB_PATH = process.env.METAO_DB || '.metao/metao.db';
const UI_ACTOR = process.env.METAO_UI_ACTOR || 'operator-ui';
const MUTATIONS_ENABLED = process.env.METAO_WEB_MUTATIONS === '1';

function cli(args: string[]): Promise<any> {
  return new Promise((resolve, reject) => {
    execFile(
      CLI_BIN,
      ['--db', DB_PATH, ...args],
      {
        cwd: __dirname,
        env: process.env,
        encoding: 'utf8',
        maxBuffer: 10 * 1024 * 1024,
      },
      (error, stdout, stderr) => {
        if (error) {
          let detail: any = null;
          try {
            detail = JSON.parse((stderr || '').trim());
          } catch {
            // Preserve the canonical process failure below.
          }
          reject(new Error(detail?.message || (stderr || error.message).trim()));
          return;
        }

        const text = (stdout || '').trim();
        if (!text) {
          resolve(null);
          return;
        }

        try {
          resolve(JSON.parse(text));
        } catch {
          reject(new Error('Canonical metaO CLI returned non-JSON output'));
        }
      },
    );
  });
}

function requireMutations(res: express.Response): boolean {
  if (MUTATIONS_ENABLED) return true;
  res.status(403).json({
    error:
      'Web mutations are disabled. Set METAO_WEB_MUTATIONS=1 only in an authorized operator environment.',
  });
  return false;
}

function withAcceptanceProof(record: any): any {
  if (record?.acceptance?.proof) {
    return { ...record, proof: record.acceptance.proof };
  }
  return record;
}

async function runtimeDetails(): Promise<any[]> {
  const runtimes = await cli(['runtimes']);
  return Promise.all(
    (runtimes || []).map(async (runtime: any) => {
      const detail = await cli(['runtime-inspect', runtime.orchestrator_id]);
      const control = detail?.control;
      return {
        ...runtime,
        disposition: control?.disposition || 'ACTIVE',
        quarantine_reason: control?.reason,
        quarantine_actor: control?.actor_id,
        quarantined_at: control?.updated_at_epoch,
      };
    }),
  );
}

async function allCertificates(): Promise<any[]> {
  const runtimes = await cli(['runtimes']);
  const groups = await Promise.all(
    (runtimes || []).map(async (runtime: any) => {
      // Bolt optimization: Fetch certificates and revocations concurrently per runtime
      // rather than sequentially, reducing latency by ~50%.
      const [certs, revocations] = await Promise.all([
        cli(['runtime-certificates', runtime.orchestrator_id]),
        cli(['runtime-certificate-revocations', runtime.orchestrator_id]),
      ]);
      const byId = new Map(
        (revocations || []).map((item: any) => [item.certificate_id, item]),
      );

      return (certs || []).map((cert: any) => {
        const revocation: any = byId.get(cert.certificate_id);
        return {
          ...cert,
          revocation_reason: revocation?.reason,
          revocation_actor: revocation?.actor_id,
          revoked_at_epoch: revocation?.revoked_at_epoch,
        };
      });
    }),
  );
  return groups.flat();
}

async function allBenchmarks(): Promise<any[]> {
  const runtimes = await cli(['runtimes']);
  const groups = await Promise.all(
    (runtimes || []).map((runtime: any) =>
      cli(['runtime-benchmarks', runtime.orchestrator_id]),
    ),
  );
  return groups.flat();
}

async function allMissions(): Promise<any[]> {
  const items = await cli(['list', '--detailed']);
  return (items || []).map((item: any) => withAcceptanceProof(item));
}

async function allEvents(): Promise<any[]> {
  const events = await cli(['events']);
  return (events || []).map((event: any) => ({
    event_id: event.event_id,
    mission_id: event.mission_id,
    kind: event.kind,
    timestamp: Number(event.occurred_at_epoch || 0) * 1000,
    data: event.payload || {},
  }));
}

async function startServer() {
  const app = express();
  const port = Number(process.env.PORT || 3000);

  app.use(securityHeaders);
  app.use(express.json({ limit: '256kb' }));

  app.get('/healthz', (_req, res) => res.status(200).send('OK'));

  app.get('/api/doctor', async (_req, res) => {
    try {
      res.json(await cli(['doctor']));
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });

  app.get('/api/runtimes', async (_req, res) => {
    try {
      res.json(await runtimeDetails());
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });

  app.get('/api/certificates', async (_req, res) => {
    try {
      res.json(await allCertificates());
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });

  app.get('/api/benchmarks', async (_req, res) => {
    try {
      res.json(await allBenchmarks());
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });

  app.get('/api/missions', async (_req, res) => {
    try {
      res.json(await allMissions());
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });

  app.get('/api/missions/:id', async (req, res) => {
    try {
      res.json(withAcceptanceProof(await cli(['inspect', req.params.id])));
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });

  app.get('/api/events', async (_req, res) => {
    try {
      res.json(await allEvents());
    } catch (error: any) {
      res.status(500).json({ error: error.message });
    }
  });

  app.post('/api/runtimes/:id/quarantine', async (req, res) => {
    if (!requireMutations(res)) return;
    try {
      res.json(
        await cli([
          'runtime-quarantine',
          req.params.id,
          '--reason',
          String(req.body?.reason || 'Operator quarantine via web console'),
          '--actor',
          UI_ACTOR,
          '--now-epoch',
          String(Date.now() / 1000),
        ]),
      );
    } catch (error: any) {
      res.status(400).json({ error: error.message });
    }
  });

  app.post('/api/runtimes/:id/restore', async (req, res) => {
    if (!requireMutations(res)) return;
    try {
      res.json(
        await cli([
          'runtime-restore',
          req.params.id,
          '--reason',
          String(req.body?.reason || 'Operator restore via web console'),
          '--actor',
          UI_ACTOR,
          '--now-epoch',
          String(Date.now() / 1000),
        ]),
      );
    } catch (error: any) {
      res.status(400).json({ error: error.message });
    }
  });

  app.post('/api/certificates/:id/revoke', async (req, res) => {
    if (!requireMutations(res)) return;
    try {
      res.json(
        await cli([
          'runtime-certificate-revoke',
          req.params.id,
          '--reason',
          String(req.body?.reason || 'Certificate revocation via web console'),
          '--actor',
          UI_ACTOR,
          '--now-epoch',
          String(Date.now() / 1000),
        ]),
      );
    } catch (error: any) {
      res.status(400).json({ error: error.message });
    }
  });

  app.post('/api/missions/:id/approve', async (req, res) => {
    if (!requireMutations(res)) return;
    try {
      const args = [
        'approve',
        req.params.id,
        '--approver',
        UI_ACTOR,
        '--now-epoch',
        String(Date.now() / 1000),
      ];
      if (req.body?.approved === false) args.push('--deny');
      await cli(args);
      res.json(withAcceptanceProof(await cli(['inspect', req.params.id])));
    } catch (error: any) {
      res.status(400).json({ error: error.message });
    }
  });

  app.post('/api/missions/:id/cancel', async (req, res) => {
    if (!requireMutations(res)) return;
    try {
      await cli([
        'cancel',
        req.params.id,
        '--now-epoch',
        String(Date.now() / 1000),
      ]);
      res.json(withAcceptanceProof(await cli(['inspect', req.params.id])));
    } catch (error: any) {
      res.status(400).json({ error: error.message });
    }
  });

  app.post('/api/examples/quickstart-accepted', async (_req, res) => {
    if (!requireMutations(res)) return;
    try {
      await cli(['run', 'examples/mission-quickstart-accepted.json']);
      res.json(
        withAcceptanceProof(await cli(['inspect', 'quickstart-accepted'])),
      );
    } catch (error: any) {
      res.status(400).json({ error: error.message });
    }
  });

  app.post('/api/examples/policy-deny', async (_req, res) => {
    if (!requireMutations(res)) return;
    try {
      await cli(['run', 'examples/mission-policy-deny.json']);
      res.json(
        withAcceptanceProof(await cli(['inspect', 'quickstart-policy-deny'])),
      );
    } catch (error: any) {
      res.status(400).json({ error: error.message });
    }
  });

  app.post('/api/missions/run', (_req, res) => {
    if (!requireMutations(res)) return;
    res.status(501).json({
      error:
        'Custom mission submission is disabled until a backend-owned policy/authority intake contract exists. Browser input cannot mint policy, verifier or acceptance authority.',
    });
  });

  if (process.env.NODE_ENV === 'production') {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (_req, res) =>
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html')),
    );
  } else {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true, host: '127.0.0.1' },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  }

  app.listen(port, '127.0.0.1', () => {
    console.log(
      `metaO operator console http://127.0.0.1:${port} (mutations=${
        MUTATIONS_ENABLED ? 'enabled' : 'read-only'
      })`,
    );
  });
}

startServer().catch((error) => {
  console.error('Fatal server startup error:', error);
  process.exit(1);
});
