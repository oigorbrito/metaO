# metaO Blocker Register

Status: NORMATIVE_FOR_PROJECT
Baseline version: V1
Applies to: repository `tihotm/metaO`
Last reconciled commit: `ffc1aae`

## Current product blockers

| BLOCKER | TYPE | CURRENT_STATUS | IMPACT |
|---|---|---|---|
| Hosted GitHub Actions pre-step failure | external infrastructure | blocked | hosted CI cannot be used as product PASS evidence |
| Exact release JSON file availability | evidence availability | blocked | independent revalidation of historical release evidence cannot proceed without the file |
| Rust-native parity as sole product language | implementation direction | in progress | current checkout is still Python-executable and should not be described as Rust-only truth |

## Current operational blockers

| BLOCKER | TYPE | CURRENT_STATUS | IMPACT |
|---|---|---|---|
| `.smag/` workspace residue | local workspace hygiene | present | untracked local state exists in the checkout |
| `experiments/rust-chassis-a/target/` residue | local workspace hygiene | present | build output exists in the checkout |

## Rules

- product blockers must not be collapsed into historical notes;
- external blockers must remain separate from implementation defects;
- a blocker is resolved only when the documented resolution condition is met.

