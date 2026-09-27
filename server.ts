import express from 'express';
import path from 'path';
import { execFile } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const CLI_BIN = process.env.METAO_CLI_BIN || 'metao';
const DB_PATH = process.env.METAO_DB || '.metao/metao.db';
const UI_ACTOR = process.env.METAO_UI_ACTOR || 'operator-ui';
const MUTATIONS_ENABLED = process.env.METAO_WEB_MUTATIONS === '1';

function cli(args: string[]): Promise<any> {
  return new Promise((resolve, reject) => {
    execFile(CLI_BIN, ['--db', DB_PATH, ...args], {
      cwd: __dirname, env: process.env, encoding: 'utf8', maxBuffer: 10 * 1024 * 1024,
    }, (error, stdout, stderr) => {
      if (error) {
        let detail: any = null;
        try { detail = JSON.parse((stderr || '').trim()); } catch {}
        reject(new Error(detail?.message || (stderr || error.message).trim()));
        return;
      }
      const text = (stdout || '').trim();
      if (!text) return resolve(null);
      try { resolve(JSON.parse(text)); }
      catch { reject(new Error('Canonical metaO CLI returned non-JSON output')); }
    });
  });
}

function requireMutations(res: express.Response): boolean {
  if (MUTATIONS_ENABLED) return true;
  res.status(403).json({ error: 'Web mutations are disabled. Set METAO_WEB_MUTATIONS=1 only in an authorized operator environment.' });
  return false;
}

async function runtimeDetails() {
  const runtimes = await cli(['runtimes']);
  return Promise.all((runtimes || []).map(async (runtime: any) => {
    try {
      const detail = await cli(['runtime-inspect', runtime.orchestrator_id]);
      const control = detail?.control;
      return { ...runtime, disposition: control?.disposition || 'ACTIVE', quarantine_reason: control?.reason, quarantine_actor: control?.actor_id, quarantined_at: control?.updated_at_epoch };
    } catch { return { ...runtime, disposition: 'ACTIVE' }; }
  }));
}
async function allCertificates() {
  const runtimes = await cli(['runtimes']);
  const groups = await Promise.all((runtimes || []).map(async (runtime: any) => {
    const certs = await cli(['runtime-certificates', runtime.orchestrator_id]);
    let revocations: any[] = [];
    try { revocations = await cli(['runtime-certificate-revocations', runtime.orchestrator_id]); } catch {}
    const byId = new Map(revocations.map((x: any) => [x.certificate_id, x]));
    return (certs || []).map((cert: any) => {
      const revocation: any = byId.get(cert.certificate_id);
      return { ...cert, revocation_reason: revocation?.reason, revocation_actor: revocation?.actor_id, revoked_at_epoch: revocation?.revoked_at_epoch };
    });
  }));
  return groups.flat();
}
async function allBenchmarks() {
  const runtimes = await cli(['runtimes']);
  return (await Promise.all((runtimes || []).map((r: any) => cli(['runtime-benchmarks', r.orchestrator_id]).catch(() => [])))).flat();
}
async function allMissions() {
  const items = await cli(['list']);
  return Promise.all((items || []).map(async (item: any) => {
    const record = await cli(['inspect', item.mission_id]).catch(() => item);
    if (record?.acceptance?.proof) record.proof = record.acceptance.proof;
    return record;
  }));
}
async function allEvents() {
  const missions = await cli(['list']);
  const groups = await Promise.all((missions || []).map((x: any) => cli(['events', x.mission_id]).catch(() => [])));
  return groups.flat().map((e: any) => ({ event_id:e.event_id, mission_id:e.mission_id, kind:e.kind, timestamp:Number(e.occurred_at_epoch || 0)*1000, data:e.payload || {} }));
}

async function startServer() {
  const app = express();
  const port = Number(process.env.PORT || 3000);
  app.use(express.json({ limit: '256kb' }));
  app.get('/healthz', (_req,res) => res.status(200).send('OK'));
  app.get('/api/doctor', async (_req,res) => { try { res.json(await cli(['doctor'])); } catch(e:any){ res.status(500).json({error:e.message}); } });
  app.get('/api/runtimes', async (_req,res) => { try { res.json(await runtimeDetails()); } catch(e:any){ res.status(500).json({error:e.message}); } });
  app.get('/api/certificates', async (_req,res) => { try { res.json(await allCertificates()); } catch(e:any){ res.status(500).json({error:e.message}); } });
  app.get('/api/benchmarks', async (_req,res) => { try { res.json(await allBenchmarks()); } catch(e:any){ res.status(500).json({error:e.message}); } });
  app.get('/api/missions', async (_req,res) => { try { res.json(await allMissions()); } catch(e:any){ res.status(500).json({error:e.message}); } });
  app.get('/api/missions/:id', async (req,res) => { try { const r=await cli(['inspect',req.params.id]); if(r?.acceptance?.proof) r.proof=r.acceptance.proof; res.json(r); } catch(e:any){ res.status(404).json({error:e.message}); } });
  app.get('/api/events', async (_req,res) => { try { res.json(await allEvents()); } catch(e:any){ res.status(500).json({error:e.message}); } });

  app.post('/api/runtimes/:id/quarantine', async (req,res) => {
    if (!requireMutations(res)) return;
    try { res.json(await cli(['runtime-quarantine',req.params.id,'--reason',String(req.body?.reason || 'Operator quarantine via web console'),'--actor',UI_ACTOR,'--now-epoch',String(Date.now()/1000)])); }
    catch(e:any){ res.status(400).json({error:e.message}); }
  });
  app.post('/api/runtimes/:id/restore', async (req,res) => {
    if (!requireMutations(res)) return;
    try { res.json(await cli(['runtime-restore',req.params.id,'--reason',String(req.body?.reason || 'Operator restore via web console'),'--actor',UI_ACTOR,'--now-epoch',String(Date.now()/1000)])); }
    catch(e:any){ res.status(400).json({error:e.message}); }
  });
  app.post('/api/certificates/:id/revoke', async (req,res) => {
    if (!requireMutations(res)) return;
    try { res.json(await cli(['runtime-certificate-revoke',req.params.id,'--reason',String(req.body?.reason || 'Certificate revocation via web console'),'--actor',UI_ACTOR,'--now-epoch',String(Date.now()/1000)])); }
    catch(e:any){ res.status(400).json({error:e.message}); }
  });
  app.post('/api/missions/:id/approve', async (req,res) => {
    if (!requireMutations(res)) return;
    try {
      const args=['approve',req.params.id,'--approver',String(req.body?.approver || UI_ACTOR),'--now-epoch',String(Date.now()/1000)];
      if(req.body?.approved===false) args.push('--deny');
      await cli(args); const r=await cli(['inspect',req.params.id]); if(r?.acceptance?.proof) r.proof=r.acceptance.proof; res.json(r);
    } catch(e:any){ res.status(400).json({error:e.message}); }
  });
  app.post('/api/missions/:id/cancel', async (req,res) => {
    if (!requireMutations(res)) return;
    try { await cli(['cancel',req.params.id,'--now-epoch',String(Date.now()/1000)]); res.json(await cli(['inspect',req.params.id])); }
    catch(e:any){ res.status(400).json({error:e.message}); }
  });

  app.post('/api/missions/run', async (req,res) => {
    if (!requireMutations(res)) return;
    const payload=req.body || {};
    try {
      if(payload?.mission?.objective==='quickstart mission' && payload?.policy?.policy_bundle_id==='quickstart-policy') {
        await cli(['run','examples/mission-quickstart-accepted.json']);
        const r=await cli(['inspect','quickstart-accepted']); if(r?.acceptance?.proof) r.proof=r.acceptance.proof; return res.json(r);
      }
      if(payload?.policy?.allowed===false) {
        await cli(['run','examples/mission-policy-deny.json']);
        const r=await cli(['inspect','quickstart-policy-deny']); if(r?.acceptance?.proof) r.proof=r.acceptance.proof; return res.json(r);
      }
      return res.status(501).json({ error:'Custom mission submission is disabled until a backend-owned policy/authority intake contract exists. Browser input cannot mint policy, verifier or acceptance authority.' });
    } catch(e:any){ res.status(400).json({error:e.message}); }
  });

  if(process.env.NODE_ENV==='production') {
    app.use(express.static(path.resolve(__dirname,'dist')));
    app.get('*',(_req,res)=>res.sendFile(path.resolve(__dirname,'dist','index.html')));
  } else {
    const { createServer:createViteServer }=await import('vite');
    const vite=await createViteServer({server:{middlewareMode:true,host:'127.0.0.1'},appType:'spa'});
    app.use(vite.middlewares);
  }
  app.listen(port,'127.0.0.1',()=>console.log(`metaO operator console http://127.0.0.1:${port} (mutations=${MUTATIONS_ENABLED?'enabled':'read-only'})`));
}
startServer().catch(err=>{console.error('Fatal server startup error:',err);process.exit(1);});
