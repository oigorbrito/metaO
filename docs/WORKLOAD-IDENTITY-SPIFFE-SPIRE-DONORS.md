# SPIFFE/SPIRE workload-identity donor pins (#159)

This repository uses SPIFFE standards and SPIRE only as **identity/attestation reference donors**. They do not become metaO policy authority, and SPIRE does not become a Core runtime dependency.

The machine-readable source of truth is:

`docs/workload-identity-spiffe-spire-donors.json`

Validate it with:

```console
python scripts/validate_workload_identity_donors.py
```

## Pinned SPIFFE standards

Repository revision:

```text
spiffe/spiffe = f97c46dfd0ff0d4e412cce5c73846a9ca32a99a2
```

Pinned specification blobs:

```text
standards/SPIFFE-ID.md
caa1bef4671a9f825cffc342d5802f430c7e1258

standards/X509-SVID.md
cec8b73004a5ea4c90c18478999dfddb1ef841bc

standards/JWT-SVID.md
8f0f39c1007ce786b5a7214ac02e21c453081270

standards/SPIFFE_Workload_API.md
f56a8761f9f906bc54e3541636253afc700f7696

standards/SPIFFE_Trust_Domain_and_Bundle.md
33746e4703f8056a5631a1de1cc2d35ffadaff35
```

## Pinned SPIRE reference implementation

```text
release = v1.15.3
annotated tag object = af69d3fae6c82db1e19107b53a311cb5ec264ec7
release commit = 2f7861ae3923caf1f57eb087fc2928d58c0fb1d2
```

Relevant implementation blobs:

```text
pkg/agent/endpoints/workload/handler.go
d67c15e01d11e9da5b3e1f935379d8fe08f31d0a

pkg/agent/agent.go
c96b52ea1762316d23e4195671857dbda196d294

cmd/spire-agent/cli/run/run.go
11b3a42dabc6403f94548cbede4637d6a00467bd
```

## Authority boundary

```text
SPIFFE_ID = AUTHENTICATED_IDENTITY_FACT
X509_SVID = SUPPORTED_REFERENCE
JWT_SVID = SUPPORTED_REFERENCE
WORKLOAD_API = ADAPTER_INTEGRATION_REFERENCE
TRUST_DOMAIN_BUNDLE = AUTHORITATIVE_TRUST_CONFIGURATION_REFERENCE

WORKLOAD_IDENTITY_AS_POLICY_AUTHORITY = REJECT
CALLER_SUPPLIED_TRUST_ROOT = REJECT
DEV_IDENTITY_AS_PRODUCTION_ATTESTATION = REJECT
SPIRE_RUNTIME_DEPENDENCY_IN_CORE = REJECT
```

This pin satisfies only the exact specification/reference-path criterion in #159. It does not claim that a real SPIRE deployment, credential rotation, cross-runtime identity mismatch tests, or two-runtime adapter evidence have executed.
