from __future__ import annotations
import argparse, json, os, socket, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

BR="br-metao168"
NODES={"a":"10.200.0.2","b":"10.200.0.3","c":"10.200.0.4"}
PORT=18080

def sh(*args, check=True):
    return subprocess.run(list(args), check=check, text=True, capture_output=True)

def sudo(*args, check=True):
    return sh("sudo", *args, check=check)

def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

def ns(name): return f"metao168-{name}"
def hv(name): return f"v168{name}h"
def nv(name): return f"v168{name}n"

def cleanup():
    for name in NODES:
        sudo("ip","netns","del",ns(name),check=False)
    sudo("ip","link","del",BR,check=False)

def setup():
    cleanup()
    sudo("ip","link","add",BR,"type","bridge")
    sudo("ip","addr","add","10.200.0.1/24","dev",BR)
    sudo("ip","link","set",BR,"up")
    for name,addr in NODES.items():
        sudo("ip","netns","add",ns(name))
        sudo("ip","link","add",hv(name),"type","veth","peer","name",nv(name))
        sudo("ip","link","set",hv(name),"master",BR)
        sudo("ip","link","set",hv(name),"up")
        sudo("ip","link","set",nv(name),"netns",ns(name))
        sudo("ip","netns","exec",ns(name),"ip","link","set","lo","up")
        sudo("ip","netns","exec",ns(name),"ip","link","set",nv(name),"name","eth0")
        sudo("ip","netns","exec",ns(name),"ip","addr","add",f"{addr}/24","dev","eth0")
        sudo("ip","netns","exec",ns(name),"ip","link","set","eth0","up")

def start_server(name):
    code=("import socket;"
          "s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);"
          f"s.bind(('0.0.0.0',{PORT}));s.listen();"
          f"label='runtime-{name}'.encode();"
          "\nwhile True:\n c,_=s.accept(); c.sendall(label); c.close()")
    return subprocess.Popen(["sudo","ip","netns","exec",ns(name),"python3","-c",code],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def probe(target, timeout=1.0):
    code=("import socket,sys;"
          f"s=socket.create_connection(('{target}',{PORT}),timeout={timeout});"
          "print(s.recv(64).decode())")
    r=sudo("ip","netns","exec",ns("a"),"python3","-c",code,check=False)
    return r.returncode, r.stdout.strip()

def wait_probe(target, expected, attempts=30):
    last=None
    for _ in range(attempts):
        last=probe(target)
        if last==(0,expected): return last
        time.sleep(0.2)
    raise RuntimeError(f"probe failed: {target} {last}")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--commit",required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--receipt",type=Path,required=True)
    a=p.parse_args()
    started=now(); t0=time.monotonic()
    servers=[]
    try:
        setup()
        servers=[start_server("b"),start_server("c")]
        wait_probe(NODES["b"],"runtime-b"); wait_probe(NODES["c"],"runtime-c")
        before={"primary":probe(NODES["b"]),"secondary":probe(NODES["c"])}
        sudo("ip","netns","exec",ns("b"),"ip","link","set","eth0","down")
        time.sleep(0.2)
        partition_primary=probe(NODES["b"],0.5)
        partition_secondary=probe(NODES["c"],0.5)
        if partition_primary[0]==0: raise RuntimeError("primary remained reachable during partition")
        if partition_secondary!=(0,"runtime-c"): raise RuntimeError("secondary unavailable during primary partition")
        sudo("ip","netns","exec",ns("b"),"ip","link","set","eth0","up")
        wait_probe(NODES["b"],"runtime-b")
        recovered=probe(NODES["b"])
        ended=now(); dur=time.monotonic()-t0
        evidence={
          "schema":"metao-real-network-chaos-v1","issue":168,
          "classification":"REAL_LOCAL_MULTI_NAMESPACE_NETWORK_CHAOS",
          "topology":{"bridge":BR,"namespaces":[ns(x) for x in NODES],"addresses":NODES},
          "before_partition":{"primary":before["primary"][1],"secondary":before["secondary"][1]},
          "partition":{"primary_unreachable":True,"secondary_reachable":True},
          "recovery":{"primary_reachable":recovered==(0,"runtime-b")},
          "real_network_namespace_isolation":True,
          "production_cluster_claim_authorized":False,
          "claim_boundary":"real Linux network namespaces/veth/bridge and link partition on hosted CI; runtime endpoints are deterministic simulated services, not external orchestrators"
        }
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
        receipt={
          "schema":"metao-scientific-gate-receipt-v1","repository":"oigorbrito/metaO","commit":a.commit,
          "gate_id":"T12","gate_level":"L6",
          "runtime_identities":["runtime-b:simulated","runtime-c:simulated"],
          "runtime_substrate":{"mode":"SIMULATED","runtimes":["runtime-b","runtime-c"]},
          "mission_lineage":["issue-168-real-network-chaos",f"github-actions:{os.environ.get('GITHUB_RUN_ID','local')}"],
          "commands":["ip netns + veth + bridge setup","partition runtime-b eth0","probe runtime-c","restore runtime-b eth0"],
          "environment":{"ci":"GitHub Actions","workflow":"Issue 168 Real Network Chaos","runner_os":os.environ.get("RUNNER_OS"),"network_substrate":"REAL_MULTI_NAMESPACE"},
          "started_at":started,"ended_at":ended,"duration_seconds":round(dur,6),"result":"PASS","failure_reason":None,
          "evidence_ids":[f"github-actions-run:{os.environ.get('GITHUB_RUN_ID','unknown')}","netns:metao168-a","netns:metao168-b","netns:metao168-c"],
          "external_systems":{"mode":"REAL","systems":["Linux network namespaces","veth pairs","Linux bridge"]}
        }
        a.receipt.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    finally:
        for proc in servers:
            proc.terminate()
            try: proc.wait(timeout=3)
            except subprocess.TimeoutExpired: proc.kill()
        cleanup()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
