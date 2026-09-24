import sys

def fix_control_plane():
    path = "D:/projetos/metaO/src/metao/control_plane.py"
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 1. Find and replace the _state definition
    # We look for 'def _state(' and the subsequent block until 'return MissionState('
    new_lines = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("def _state("):
            # Replace the definition
            new_lines.append("def _state(\n")
            new_lines.append("    mission_id: str,\n")
            new_lines.append("    status: MissionStatus,\n")
            new_lines.append("    *,\n")
            new_lines.append("    attempts: tuple[MissionAttempt, ...] = (),\n")
            new_lines.append("    history: tuple[MissionStatus, ...],\n")
            new_lines.append("    plan: ExecutionPlan | None = None,\n")
            new_lines.append("    completed_steps: frozenset[str] = frozenset(),\n")
            new_lines.append(") -> MissionState:\n")
            new_lines.append("    return MissionState(\n")
            new_lines.append("        mission_id=mission_id,\n")
            new_lines.append("        status=status,\n")
            new_lines.append("        attempts=attempts,\n")
            new_lines.append("        history=history,\n")
            new_lines.append("        plan=plan,\n")
            new_lines.append("        completed_steps=completed_steps,\n")
            new_lines.append("    )\n")
            # Skip the old definition
            while i < len(lines) and not lines[i].strip().startswith("def") and "return MissionState" not in lines[i]:
                i += 1
            # We need to skip until the end of the function block
            # Since the function is simple, we can just skip until the next blank line or def
            while i < len(lines) and not (lines[i].strip() == "" or lines[i].strip().startswith("def")):
                i += 1
        else:
            new_lines.append(lines[i])
            i += 1

    # Note: The above manual line replacement is risky. 
    # Let's use a better approach: Replace the specific block in the whole text.
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Fix definition
    old_def = """def _state(
    mission_id: str,
    status: MissionStatus,
    *,
    attempts: tuple[MissionAttempt, ...] = (),
    history: tuple[MissionStatus, ...],
) -> MissionState:
    return MissionState(
        mission_id=mission_id,
        status=status,
        attempts=attempts,
        history=history,
    )"""
    
    # The file has weird indentation and double newlines. 
    # I'll use a regex or a more flexible replacement.
    import re
    
    # This pattern matches the function from 'def _state' to the closing ')' of MissionState
    pattern = re.compile(r'def _state\(.*?\)\s-> MissionState:\s+return MissionState\(.*?\)', re.DOTALL)
    
    replacement_def = """def _state(
    mission_id: str,
    status: MissionStatus,
    *,
    attempts: tuple[MissionAttempt, ...] = (),
    history: tuple[MissionStatus, ...],
    plan: ExecutionPlan | None = None,
    completed_steps: frozenset[str] = frozenset(),
) -> MissionState:
    return MissionState(
        mission_id=mission_id,
        status=status,
        attempts=attempts,
        history=history,
        plan=plan,
        completed_steps=completed_steps,
    )"""
    
    content = pattern.sub(replacement_def, content)
    
    # 2. Now fix the call sites in execute_mission
    # We need to find calls to _state(...) and add plan=plan, completed_steps=completed_steps
    
    # This is tricky because of the formatting. 
    # I will look for '_state(' and find the matching ')'
    
    # We want to replace:
    # _state(
    #     mission.mission_id,
    #     terminal,
    #     attempts=tuple(attempt_records),
    #     history=tuple(history),
    # )
    # with:
    # _state(
    #     mission.mission_id,
    #     terminal,
    #     attempts=tuple(attempt_records),
    #     history=tuple(history),
    #     plan=plan,
    #     completed_steps=completed_steps,
    # )
    
    def add_plan_args(match):
        call_text = match.group(0)
        if "plan=" in call_text:
            return call_text
        # Insert before the last closing parenthesis
        return call_text.replace(")", ",\n                plan=plan,\n                completed_steps=completed_steps,\n            )")

    # This regex matches _state( ... )
    call_pattern = re.compile(r'_state\s*\([^\)]*?\)', re.DOTALL)
    content = call_pattern.sub(add_plan_args, content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully updated _state and its call sites.")

if __name__ == "__main__":
    fix_control_plane()
