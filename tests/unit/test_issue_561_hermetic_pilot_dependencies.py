from pathlib import Path


WORKFLOWS = (
    Path(".github/workflows/project-multi-provider-pilot.yml"),
    Path(".github/workflows/project-multi-provider-pilot-self-hosted.yml"),
)


def test_operational_pilot_workflows_use_hermetic_dependency_path():
    for workflow in WORKFLOWS:
        text = workflow.read_text(encoding="utf-8")

        assert "install_hermetic_pilot_runtime.py" in text
        assert "run_project_multi_provider_pilot_hermetic.py" in text
        assert "dependency_identity" in text
        assert "bootstrap_lock_sha256" in text
        assert "runtime_requirements_sha256" in text
        assert "runtime_authority_openai_agents_wheel_sha256" in text

        assert "pip install --upgrade pip" not in text
        assert "pip install 'openai-agents==0.20.0'" not in text
        assert "scripts/project_multi_provider_pilot.py" not in text


def test_hosted_operational_pilot_uses_python_313():
    text = WORKFLOWS[0].read_text(encoding="utf-8")
    assert "python-version: '3.13'" in text
    assert "python-version: '3.12'" not in text
