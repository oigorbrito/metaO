import re

def refactor_control_plane():
    path = "D:/projetos/metaO/src/metao/control_plane.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Inject plan and completed_steps before the loop
    # Find the start of the loop
    loop_pattern = r"for attempt_index in range\(max_attempts\):"
    match = re.search(loop_pattern, content)
    if not match:
        print("Loop not found")
        return

    loop_start = match.start()
    
    # We insert setup variables before the loop. 
    # We need to find the indentation of the loop.
    line_start = content.rfind("\n", 0, loop_start) + 1
    indent = content[line_start:loop_start]
    
    setup = (
        f"{indent}plan = DefaultLinearPlan(plan_id=execution_id_prefix, max_attempts=max_attempts)\n"
        f"{indent}completed_steps = frozenset()\n"
        f"{indent}attempt_index = 0\n"
    )
    
    content = content[:loop_start] + setup + content[loop_start:]
    
    # 2. Replace the loop header
    # Find the loop again since we shifted indices
    match = re.search(loop_pattern, content)
    loop_start = match.start()
    loop_end = match.end()
    
    new_header = "while (step := plan.get_next_step(completed_steps)) is not None:"
    content = content[:loop_start] + new_header + content[loop_end:]
    
    # 3. Update attempt_index inside the loop
    # Insert attempt_index calculation at the start of the loop body
    loop_header_end = content.find(":", loop_start) + 1
    body_indent = indent + "    "
    index_calc = f"\n{body_indent}attempt_index = int(step.step_id.split('_')[1]) - 1"
    content = content[:loop_header_end] + index_calc + content[loop_header_end:]
    
    # 4. Update completed_steps on ACCEPT
    success_marker = "if outcome.acceptance.decision is AcceptanceDecision.ACCEPT:"
    success_pos = content.find(success_marker)
    if success_pos != -1:
        # Find end of that line
        line_end = content.find("\n", success_pos)
        # Add the set update on the next line with proper indentation
        success_update = f"\n{body_indent}    completed_steps |= {{step.step_id}}"
        content = content[:line_end] + success_update + content[line_end:]

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Refactor complete")

if __name__ == "__main__":
    refactor_control_plane()
