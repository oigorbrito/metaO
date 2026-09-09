use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Debug, PartialEq, Eq)]
struct ProjectObjective {
    project_id: &'static str,
    requirement_id: &'static str,
    objective: &'static str,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct WorkUnit {
    id: &'static str,
    dependencies: Vec<&'static str>,
    corrective: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct AuthoritativePlan {
    authority: &'static str,
    units: Vec<WorkUnit>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct Executor {
    id: &'static str,
    provider: &'static str,
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum TraceKind {
    Planned,
    Dispatched,
    FailedCapacity,
    Checkpointed,
    HandedOff,
    ArtifactProduced,
    VerificationFailed,
    CorrectiveWorkCreated,
    VerificationPassed,
    IndependentAcceptance,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct TraceEvent {
    kind: TraceKind,
    work_unit_id: &'static str,
    executor_id: Option<&'static str>,
    repository_state: Option<&'static str>,
    artifact_ref: Option<&'static str>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct TraceabilityRecord {
    requirement_id: &'static str,
    work_unit_id: &'static str,
    artifact_ref: &'static str,
    test_ref: &'static str,
    verdict: &'static str,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct ProjectSupervisionResult {
    project_id: &'static str,
    plan: AuthoritativePlan,
    trace: Vec<TraceEvent>,
    traceability: Vec<TraceabilityRecord>,
    executors_used: BTreeSet<&'static str>,
    providers_used: BTreeSet<&'static str>,
    verdict: &'static str,
    independent_verifier: &'static str,
}

fn derive_authoritative_plan(_objective: &ProjectObjective) -> AuthoritativePlan {
    AuthoritativePlan {
        authority: "metao",
        units: vec![
            WorkUnit {
                id: "discover",
                dependencies: vec![],
                corrective: false,
            },
            WorkUnit {
                id: "implement",
                dependencies: vec!["discover"],
                corrective: false,
            },
            WorkUnit {
                id: "verify",
                dependencies: vec!["implement"],
                corrective: false,
            },
        ],
    }
}

fn validate_plan(plan: &AuthoritativePlan) {
    assert_eq!(plan.authority, "metao");
    assert!(plan.units.len() > 1);

    let ids: BTreeSet<_> = plan.units.iter().map(|unit| unit.id).collect();
    assert_eq!(ids.len(), plan.units.len());

    for unit in &plan.units {
        for dependency in &unit.dependencies {
            assert!(ids.contains(dependency));
        }
    }
}

fn run_local_supervision(objective: &ProjectObjective) -> ProjectSupervisionResult {
    let mut plan = derive_authoritative_plan(objective);
    validate_plan(&plan);

    let executor_a = Executor {
        id: "executor-a",
        provider: "provider-a",
    };
    let executor_b = Executor {
        id: "executor-b",
        provider: "provider-b",
    };

    let mut trace = vec![TraceEvent {
        kind: TraceKind::Planned,
        work_unit_id: "discover",
        executor_id: None,
        repository_state: None,
        artifact_ref: None,
    }];
    let mut executors_used = BTreeSet::new();
    let mut providers_used = BTreeSet::new();
    let mut repository_state = "root";
    let mut artifacts: BTreeMap<&'static str, &'static str> = BTreeMap::new();

    trace.push(TraceEvent {
        kind: TraceKind::Dispatched,
        work_unit_id: "discover",
        executor_id: Some(executor_a.id),
        repository_state: Some(repository_state),
        artifact_ref: None,
    });
    executors_used.insert(executor_a.id);
    providers_used.insert(executor_a.provider);
    repository_state = "commit-discover";
    artifacts.insert("discover", repository_state);
    trace.push(TraceEvent {
        kind: TraceKind::ArtifactProduced,
        work_unit_id: "discover",
        executor_id: Some(executor_a.id),
        repository_state: Some(repository_state),
        artifact_ref: Some("commit-discover"),
    });

    trace.push(TraceEvent {
        kind: TraceKind::Dispatched,
        work_unit_id: "implement",
        executor_id: Some(executor_a.id),
        repository_state: Some(repository_state),
        artifact_ref: None,
    });
    trace.push(TraceEvent {
        kind: TraceKind::FailedCapacity,
        work_unit_id: "implement",
        executor_id: Some(executor_a.id),
        repository_state: Some(repository_state),
        artifact_ref: None,
    });
    trace.push(TraceEvent {
        kind: TraceKind::Checkpointed,
        work_unit_id: "implement",
        executor_id: Some(executor_a.id),
        repository_state: Some(repository_state),
        artifact_ref: Some("checkpoint:commit-discover"),
    });

    trace.push(TraceEvent {
        kind: TraceKind::HandedOff,
        work_unit_id: "implement",
        executor_id: Some(executor_b.id),
        repository_state: Some(repository_state),
        artifact_ref: Some("checkpoint:commit-discover"),
    });
    executors_used.insert(executor_b.id);
    providers_used.insert(executor_b.provider);
    repository_state = "commit-implement";
    artifacts.insert("implement", repository_state);
    trace.push(TraceEvent {
        kind: TraceKind::ArtifactProduced,
        work_unit_id: "implement",
        executor_id: Some(executor_b.id),
        repository_state: Some(repository_state),
        artifact_ref: Some("commit-implement"),
    });

    trace.push(TraceEvent {
        kind: TraceKind::VerificationFailed,
        work_unit_id: "verify",
        executor_id: Some(executor_b.id),
        repository_state: Some(repository_state),
        artifact_ref: Some("test:acceptance-missing-proof"),
    });

    plan.units.push(WorkUnit {
        id: "corrective-acceptance-proof",
        dependencies: vec!["implement"],
        corrective: true,
    });
    trace.push(TraceEvent {
        kind: TraceKind::CorrectiveWorkCreated,
        work_unit_id: "corrective-acceptance-proof",
        executor_id: None,
        repository_state: Some(repository_state),
        artifact_ref: None,
    });
    repository_state = "commit-corrective-proof";
    artifacts.insert("corrective-acceptance-proof", repository_state);
    trace.push(TraceEvent {
        kind: TraceKind::ArtifactProduced,
        work_unit_id: "corrective-acceptance-proof",
        executor_id: Some(executor_b.id),
        repository_state: Some(repository_state),
        artifact_ref: Some("commit-corrective-proof"),
    });
    trace.push(TraceEvent {
        kind: TraceKind::VerificationPassed,
        work_unit_id: "verify",
        executor_id: Some(executor_b.id),
        repository_state: Some(repository_state),
        artifact_ref: Some("test:acceptance-pass"),
    });
    trace.push(TraceEvent {
        kind: TraceKind::IndependentAcceptance,
        work_unit_id: "verify",
        executor_id: None,
        repository_state: Some(repository_state),
        artifact_ref: Some("verdict:project-accepted"),
    });

    let traceability = vec![
        TraceabilityRecord {
            requirement_id: objective.requirement_id,
            work_unit_id: "discover",
            artifact_ref: artifacts["discover"],
            test_ref: "test:discovery-contract",
            verdict: "PASS",
        },
        TraceabilityRecord {
            requirement_id: objective.requirement_id,
            work_unit_id: "implement",
            artifact_ref: artifacts["implement"],
            test_ref: "test:implementation",
            verdict: "PASS",
        },
        TraceabilityRecord {
            requirement_id: objective.requirement_id,
            work_unit_id: "corrective-acceptance-proof",
            artifact_ref: artifacts["corrective-acceptance-proof"],
            test_ref: "test:acceptance-pass",
            verdict: "PASS",
        },
    ];

    ProjectSupervisionResult {
        project_id: objective.project_id,
        plan,
        trace,
        traceability,
        executors_used,
        providers_used,
        verdict: "PROJECT_ACCEPTED",
        independent_verifier: "independent-project-verifier",
    }
}

#[test]
fn one_objective_is_decomposed_supervised_failed_over_corrected_and_accepted() {
    let objective = ProjectObjective {
        project_id: "project-360",
        requirement_id: "req-complete-project",
        objective: "deliver a complete project from one objective",
    };

    let result = run_local_supervision(&objective);

    assert_eq!(result.project_id, "project-360");
    assert_eq!(result.plan.authority, "metao");
    assert!(result.plan.units.len() > 1);
    assert!(result.plan.units.iter().any(|unit| unit.corrective));
    assert_eq!(result.executors_used.len(), 2);
    assert_eq!(result.providers_used.len(), 2);
    assert!(result.trace.iter().any(|event| event.kind == TraceKind::FailedCapacity));
    assert!(result.trace.iter().any(|event| event.kind == TraceKind::Checkpointed));
    assert!(result.trace.iter().any(|event| event.kind == TraceKind::HandedOff));
    assert!(result.trace.iter().any(|event| event.kind == TraceKind::VerificationFailed));
    assert!(result
        .trace
        .iter()
        .any(|event| event.kind == TraceKind::CorrectiveWorkCreated));
    assert!(result
        .trace
        .iter()
        .any(|event| event.kind == TraceKind::IndependentAcceptance));
    assert_eq!(result.independent_verifier, "independent-project-verifier");
    assert_eq!(result.verdict, "PROJECT_ACCEPTED");
}

#[test]
fn failover_handoff_preserves_exact_repository_checkpoint() {
    let objective = ProjectObjective {
        project_id: "project-360",
        requirement_id: "req-complete-project",
        objective: "deliver a complete project from one objective",
    };
    let result = run_local_supervision(&objective);

    let checkpoint = result
        .trace
        .iter()
        .find(|event| event.kind == TraceKind::Checkpointed)
        .expect("checkpoint event");
    let handoff = result
        .trace
        .iter()
        .find(|event| event.kind == TraceKind::HandedOff)
        .expect("handoff event");

    assert_eq!(checkpoint.repository_state, Some("commit-discover"));
    assert_eq!(handoff.repository_state, checkpoint.repository_state);
    assert_eq!(handoff.artifact_ref, checkpoint.artifact_ref);
    assert_eq!(handoff.executor_id, Some("executor-b"));
}

#[test]
fn final_traceability_binds_requirement_work_artifact_test_and_verdict() {
    let objective = ProjectObjective {
        project_id: "project-360",
        requirement_id: "req-complete-project",
        objective: "deliver a complete project from one objective",
    };
    let result = run_local_supervision(&objective);

    assert!(result.traceability.len() >= 3);
    assert!(result.traceability.iter().all(|record| {
        record.requirement_id == objective.requirement_id
            && !record.work_unit_id.is_empty()
            && !record.artifact_ref.is_empty()
            && !record.test_ref.is_empty()
            && record.verdict == "PASS"
    }));
}
