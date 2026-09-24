def fix_control_plane():
    path = "D:/projetos/metaO/src/metao/control_plane.py"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Replace the _state definition
    # Find the function starting with 'def _state(' and ending before the next 'def' or end of file
    # Since the file has weird double newlines, we use a more robust regex.
    
    # This pattern matches 'def _state' and everything until the return MissionState(...) line.
    # We use [^def] logically or just look for the function structure.
    
    # Because of the double newlines in the file, we normalize newlines temporarily for the replacement
    # or we just match them.
    
    # Let's try a simpler replacement: replace the specific strings.
    
    # Instead of regex, let's split by line and rebuild.
    lines = content.splitlines()
    new_lines = []
    in_state_def = False
    
    for line in lines:
        if "def _state(" in line:
            in_state_def = True
            new_lines.append("def _state(")
            new_lines.append("    mission_id: str,")
            new_lines.append("    status: MissionStatus,")
            new_lines.append("    *,")
            new_lines.append("    attempts: tuple[MissionAttempt, ...] = (),")
            new_lines.append("    history: tuple[MissionStatus, ...],")
            new_lines.append("    plan: ExecutionPlan | None = None,")
            new_lines.append("    completed_steps: frozenset[str] = frozenset(),")
            new_lines.append(") -> MissionState:")
            new_lines.append("    return MissionState(")
            new_lines.append("        mission_id=mission_id,")
            new_lines.append("        status=status,")
            new_lines.append("        attempts=attempts,")
            new_lines.append("        history=history,")
            new_lines.append("        plan=plan,")
            new_lines.append("        completed_steps=completed_steps,")
            new_lines.append("    )")
            continue
        
        if in_state_def:
            if "return MissionState(mission_id, status, attempts, history)" in line:
                in_state_def = False
                continue
            # Skip the original parameters
            if any(x in line for x in ["mission_id:", "status:", "*,", "attempts:", "history:"]):
                continue
            if ") -> MissionState:" in line:
                continue
            # If we hit a blank line after the return, we are done.
            if line.strip() == "":
                # Keep one blank line to separate functions
                new_lines.append("")
                in_state_def = False
                continue
        
        new_lines.append(line)

    content = "\n".join(new_lines)

    # 2. Replace call sites
    # We look for '_state(' and we want to append the new arguments.
    # This is harder because calls are multi-line.
    
    # We'll find all indices of '_state('
    # Then we find the closing ')' for each.
    
    final_content = ""
    last_pos = 0
    while True:
        pos = content.find("_state(", last_pos)
        if pos == -1:
            final_content += content[last_pos:]
            break
        
        final_content += content[last_pos:pos]
        
        # Find the matching closing parenthesis
        bracket_count = 0
        end_pos = -1
        for i in range(pos + 6, len(content)):
            if content[i] == '(':
                bracket_count += 1
            elif content[i] == ')':
                if bracket_count == 0:
                    end_pos = i
                    break
                bracket_count -= 1
        
        if end_pos == -1:
            # Should not happen
            final_content += content[pos:pos+7]
            last_pos = pos + 7
            continue
            
        call_body = content[pos:end_pos+1]
        
        # If it's the definition, it was already handled, but just in case:
        if "def _state" in call_body:
            final_content += call_body
        else:
            # Replace ')' with the new arguments
            # We assume the call ends with ')'
            # We insert before the last ')'
            
            # If it's a multi-line call, we add them at the end.
            if "\n" in call_body:
                # Try to find the last argument's line
                # We replace the last ')' with the new args.
                updated_call = call_body.replace(")", ",\n                plan=plan,\n                completed_steps=completed_steps,\n            )")
                final_content += updated_call
            else:
                updated_call = call_body.replace(")", ", plan=plan, completed_steps=completed_steps)")
                final_content += updated_call
                
        last_pos = end_pos + 1
        
    with open(path, "w", encoding="utf-8") as f:
        f.write(final_content)
    print("Successfully updated _state and its call sites.")

if __name__ == "__main__":
    fix_control_plane()
