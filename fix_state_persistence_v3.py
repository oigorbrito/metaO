import re

def fix_control_plane_v3():
    path = "D:/projetos/metaO/src/metao/control_plane.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Clean up any corrupted state definition first
    # We search for the region from 'def _state(' to the end of the function
    # and replace it with a clean one.
    
    # This regex finds the function definition and its body
    # It looks for 'def _state' and everything until the first line that starts with 'def ' or 'class ' or '__all__'
    # This is risky, so I'll use a more precise boundary.
    
    # I'll find 'def _state(' and then find the 'return MissionState(' call.
    # Then I'll replace everything between those.
    
    start_def = content.find("def _state(")
    if start_def != -1:
        # Find the end of the return statement
        end_ret = content.find(")", start_def)
        # Wait, return MissionState(...) has its own closing paren.
        # Let's find the return line.
        ret_start = content.find("return MissionState", start_def)
        if ret_start != -1:
            # Find the closing paren of MissionState(
            bracket_count = 0
            ret_end = -1
            for i in range(ret_start, len(content)):
                if content[i] == '(':
                    bracket_count += 1
                elif content[i] == ')':
                    bracket_count -= 1
                    if bracket_count == 0:
                        ret_end = i + 1
                        break
            
            if ret_end != -1:
                # Replace the corrupted block
                clean_def = """def _state(
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
                content = content[:start_def] + clean_def + content[ret_end:]

    # 2. Now handle call sites
    # To avoid corrupting the definition we just wrote, we will only replace calls 
    # that are NOT preceded by 'def ' on the same or previous lines.
    
    # A better way: search for '_state(' and check if it's part of 'def _state('
    
    final_content = ""
    last_pos = 0
    while True:
        pos = content.find("_state(", last_pos)
        if pos == -1:
            final_content += content[last_pos:]
            break
        
        # Check if this is the definition
        # Look back a few characters for 'def '
        is_def = False
        if pos > 4:
            prefix = content[pos-4:pos]
            if "def " in prefix:
                is_def = True
        
        if is_def:
            # It's the definition, skip it
            # Find the end of the call (the closing paren of the parameter list)
            bracket_count = 0
            end_pos = -1
            for i in range(pos + 7, len(content)):
                if content[i] == '(':
                    bracket_count += 1
                elif content[i] == ')':
                    if bracket_count == 0:
                        end_pos = i + 1
                        break
                    bracket_count -= 1
            
            if end_pos == -1:
                final_content += content[pos:pos+7]
                last_pos = pos + 7
                continue
            
            final_content += content[last_pos:end_pos]
            last_pos = end_pos
            continue

        # It's a call site
        final_content += content[last_pos:pos]
        
        # Find the closing paren of the call
        bracket_count = 0
        end_pos = -1
        for i in range(pos + 7, len(content)):
            if content[i] == '(':
                bracket_count += 1
            elif content[i] == ')':
                if bracket_count == 0:
                    end_pos = i + 1
                    break
                bracket_count -= 1
        
        if end_pos == -1:
            final_content += content[pos:pos+7]
            last_pos = pos + 7
            continue
            
        call_text = content[pos:end_pos]
        
        # Add plan and completed_steps
        if "plan=" in call_text:
            # Already fixed
            final_content += call_text
        else:
            # Multi-line or single line?
            if "\n" in call_text:
                # Replace the last ')' with new arguments
                # This is still a bit risky, let's be precise.
                updated_call = call_text.rstrip().rstrip(')') + ",\n                plan=plan,\n                completed_steps=completed_steps,\n            )"
                final_content += updated_call
            else:
                updated_call = call_text.replace(")", ", plan=plan, completed_steps=completed_steps)")
                final_content += updated_call
                
        last_pos = end_pos

    with open(path, "w", encoding="utf-8") as f:
        f.write(final_content)
    print("Fixed corruption and updated call sites.")

if __name__ == "__main__":
    fix_control_plane_v3()
