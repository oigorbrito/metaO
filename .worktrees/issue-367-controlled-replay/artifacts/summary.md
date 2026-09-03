# Controlled Replay Summary

Date: 2026-09-03

Initial HEAD: 2d2f74aab9f1329ca464ddafd685ab4dd2ac8d23
Final HEAD: 0f05957456f553a4bcea0506880ff4108d5a1118
Donor pin: issue-orchestrator/issue-orchestrator@26564aac4a02afc0989966ec2cd3e190884ba177
Protocol version: FROZEN_PROTOCOL_V1
Execution mode: CONTROLLED_REPLAY

Replay matrix:
- P2/F1: PASS
- P2/F2: PASS
- P3/F1: PASS
- P3/F2: PASS

Repetitions:
- 5 valid repetitions per fixture

Live metrics:
- LLM_INPUT_TOKENS = NOT_TESTED
- LLM_OUTPUT_TOKENS = NOT_TESTED
- UNDERLYING_GITHUB_CALLS = NOT_TESTED
- PRIMARY_GITHUB_REQUEST_COUNT = NOT_APPLICABLE
- FALLBACK_GITHUB_REQUEST_COUNT = NOT_APPLICABLE
- WRITE_VERIFY_REQUEST_COUNT = NOT_APPLICABLE

Blockers:
- live GitHub metrics remain unavailable in this environment

Deviations:
- local controlled replay reconstructed from authoritative inputs because replay extension file was not materialized in the current checkout
