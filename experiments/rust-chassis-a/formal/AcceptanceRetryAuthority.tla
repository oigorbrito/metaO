---------------- MODULE AcceptanceRetryAuthority ----------------
EXTENDS Naturals, TLC

CONSTANT MaxGeneration

VerifierStates == {"UNKNOWN", "PASS", "FAIL"}
Decisions == {"NOT_DONE", "ACCEPTED", "BLOCKED"}

VARIABLES generation,
          runtimeDoneGeneration,
          evidenceGeneration,
          evidenceFresh,
          verifierState,
          recoveryComplete,
          retryEnabled,
          decision,
          acceptedGeneration

vars == <<generation,
          runtimeDoneGeneration,
          evidenceGeneration,
          evidenceFresh,
          verifierState,
          recoveryComplete,
          retryEnabled,
          decision,
          acceptedGeneration>>

Init ==
    /\ generation = 1
    /\ runtimeDoneGeneration = 0
    /\ evidenceGeneration = 0
    /\ evidenceFresh = FALSE
    /\ verifierState = "UNKNOWN"
    /\ recoveryComplete = FALSE
    /\ retryEnabled = FALSE
    /\ decision = "NOT_DONE"
    /\ acceptedGeneration = 0

RuntimeDone(g) ==
    /\ g \in 1..generation
    /\ runtimeDoneGeneration' = g
    /\ UNCHANGED <<generation, evidenceGeneration, evidenceFresh,
                   verifierState, recoveryComplete, retryEnabled,
                   decision, acceptedGeneration>>

ObserveEvidence(g, fresh, verifier) ==
    /\ decision = "NOT_DONE"
    /\ g \in 1..generation
    /\ fresh \in BOOLEAN
    /\ verifier \in VerifierStates
    /\ evidenceGeneration' = g
    /\ evidenceFresh' = fresh
    /\ verifierState' = verifier
    /\ UNCHANGED <<generation, runtimeDoneGeneration,
                   recoveryComplete, retryEnabled,
                   decision, acceptedGeneration>>

CompleteRecovery ==
    /\ decision = "NOT_DONE"
    /\ recoveryComplete' = TRUE
    /\ retryEnabled' = TRUE
    /\ UNCHANGED <<generation, runtimeDoneGeneration,
                   evidenceGeneration, evidenceFresh, verifierState,
                   decision, acceptedGeneration>>

IncompleteRecovery ==
    /\ decision = "NOT_DONE"
    /\ recoveryComplete' = FALSE
    /\ retryEnabled' = FALSE
    /\ UNCHANGED <<generation, runtimeDoneGeneration,
                   evidenceGeneration, evidenceFresh, verifierState,
                   decision, acceptedGeneration>>

Failover ==
    /\ decision = "NOT_DONE"
    /\ generation < MaxGeneration
    /\ generation' = generation + 1
    /\ runtimeDoneGeneration' = 0
    /\ evidenceGeneration' = 0
    /\ evidenceFresh' = FALSE
    /\ verifierState' = "UNKNOWN"
    /\ recoveryComplete' = FALSE
    /\ retryEnabled' = FALSE
    /\ decision' = "NOT_DONE"
    /\ acceptedGeneration' = 0

Accept ==
    /\ decision = "NOT_DONE"
    /\ evidenceGeneration = generation
    /\ evidenceFresh = TRUE
    /\ verifierState = "PASS"
    /\ decision' = "ACCEPTED"
    /\ acceptedGeneration' = generation
    /\ UNCHANGED <<generation, runtimeDoneGeneration,
                   evidenceGeneration, evidenceFresh, verifierState,
                   recoveryComplete, retryEnabled>>

Block ==
    /\ decision = "NOT_DONE"
    /\ verifierState = "FAIL"
    /\ decision' = "BLOCKED"
    /\ UNCHANGED <<generation, runtimeDoneGeneration,
                   evidenceGeneration, evidenceFresh, verifierState,
                   recoveryComplete, retryEnabled, acceptedGeneration>>

Next ==
    \/ \E g \in 1..generation: RuntimeDone(g)
    \/ \E g \in 1..generation, fresh \in BOOLEAN, v \in VerifierStates:
           ObserveEvidence(g, fresh, v)
    \/ CompleteRecovery
    \/ IncompleteRecovery
    \/ Failover
    \/ Accept
    \/ Block

Spec == Init /\ [][Next]_vars

OrchestratorDoneIsNotAcceptance ==
    runtimeDoneGeneration = generation => decision # "ACCEPTED" \/
        (evidenceGeneration = generation /\ evidenceFresh /\ verifierState = "PASS")

AcceptedRequiresIndependentFreshPass ==
    decision = "ACCEPTED" =>
        /\ acceptedGeneration = generation
        /\ evidenceGeneration = generation
        /\ evidenceFresh = TRUE
        /\ verifierState = "PASS"

StaleEvidenceCannotAcceptCurrentGeneration ==
    (evidenceGeneration # generation \/ ~evidenceFresh) => decision # "ACCEPTED"

IncompleteRecoveryCannotEnableRetry ==
    ~recoveryComplete => ~retryEnabled

UnknownNeverAccepts ==
    verifierState = "UNKNOWN" => decision # "ACCEPTED"

OldGenerationDoneCannotAcceptCurrent ==
    (runtimeDoneGeneration > 0 /\ runtimeDoneGeneration # generation) =>
        decision # "ACCEPTED" \/ acceptedGeneration = generation

AcceptedGenerationMatchesCurrent ==
    decision = "ACCEPTED" => acceptedGeneration = generation

=============================================================================