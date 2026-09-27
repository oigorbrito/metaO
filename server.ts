import express from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { metaoEngine } from './src/lib/metaoEngine';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = process.env.PORT || 3000;

  app.use(cors());
  app.use(express.json());

  // Health probe endpoint
  app.get('/healthz', (_req, res) => {
    res.status(200).send('OK');
  });

  // API Routes

  // Doctor
  app.get('/api/doctor', (_req, res) => {
    try {
      const report = metaoEngine.getDoctorReport();
      res.json(report);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Runtimes
  app.get('/api/runtimes', (_req, res) => {
    try {
      const runtimes = metaoEngine.getRuntimes();
      res.json(runtimes);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post('/api/runtimes/:id/quarantine', (req, res) => {
    try {
      const { reason, actor } = req.body;
      const runtime = metaoEngine.quarantineRuntime(
        req.params.id,
        reason || 'Operator quarantined runtime',
        actor || 'operator'
      );
      res.json(runtime);
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  app.post('/api/runtimes/:id/restore', (req, res) => {
    try {
      const { reason, actor } = req.body;
      const runtime = metaoEngine.restoreRuntime(
        req.params.id,
        reason || 'Operator restored runtime',
        actor || 'operator'
      );
      res.json(runtime);
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  // Certifications
  app.get('/api/certificates', (req, res) => {
    try {
      const orchestratorId = req.query.orchestrator_id as string | undefined;
      const certs = metaoEngine.getCertifications(orchestratorId);
      res.json(certs);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post('/api/certificates/:id/revoke', (req, res) => {
    try {
      const { reason, actor } = req.body;
      const cert = metaoEngine.revokeCertificate(
        req.params.id,
        reason || 'Security or conformance revocation',
        actor || 'governance-authority'
      );
      res.json(cert);
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  // Benchmarks
  app.get('/api/benchmarks', (req, res) => {
    try {
      const orchestratorId = req.query.orchestrator_id as string | undefined;
      const benchmarks = metaoEngine.getBenchmarks(orchestratorId);
      res.json(benchmarks);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Missions
  app.get('/api/missions', (_req, res) => {
    try {
      const missions = metaoEngine.getMissions();
      res.json(missions);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.get('/api/missions/:id', (req, res) => {
    try {
      const mission = metaoEngine.getMission(req.params.id);
      if (!mission) {
        return res.status(404).json({ error: `Mission not found: ${req.params.id}` });
      }
      res.json(mission);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  app.post('/api/missions/run', (req, res) => {
    try {
      const record = metaoEngine.runMission(req.body);
      res.json(record);
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  app.post('/api/missions/:id/approve', (req, res) => {
    try {
      const { approver, approved, reason } = req.body;
      const record = metaoEngine.approveMission(
        req.params.id,
        approver || 'operator',
        approved !== false,
        reason
      );
      res.json(record);
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  app.post('/api/missions/:id/cancel', (req, res) => {
    try {
      const { reason } = req.body;
      const record = metaoEngine.cancelMission(req.params.id, reason);
      res.json(record);
    } catch (err: any) {
      res.status(400).json({ error: err.message });
    }
  });

  // Events
  app.get('/api/events', (req, res) => {
    try {
      const missionId = req.query.mission_id as string | undefined;
      const events = metaoEngine.getEvents(missionId);
      res.json(events);
    } catch (err: any) {
      res.status(500).json({ error: err.message });
    }
  });

  // Vite middleware in dev or static serving in prod
  const isProduction = process.env.NODE_ENV === 'production';

  if (isProduction) {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (_req, res) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
    });
  } else {
    const { createServer: createViteServer } = await import('vite');
    const vite = await createViteServer({
      server: { middlewareMode: true, host: '0.0.0.0' },
      appType: 'custom',
    });
    app.use(vite.middlewares);

    app.use('*', async (req, res, next) => {
      try {
        const url = req.originalUrl;
        let template = fs.readFileSync(path.resolve(__dirname, 'index.html'), 'utf-8');
        template = await vite.transformIndexHtml(url, template);
        res.status(200).set({ 'Content-Type': 'text/html' }).end(template);
      } catch (e: any) {
        if (vite) vite.ssrFixStacktrace(e);
        next(e);
      }
    });
  }

  app.listen(Number(PORT), '0.0.0.0', () => {
    console.log(`metaO Control Plane running on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Fatal server startup error:', err);
  process.exit(1);
});
