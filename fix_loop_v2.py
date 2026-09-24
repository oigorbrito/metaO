with open("D:/projetos/metaO/src/metao/control_plane.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the corrupted while loop
# Look for 'while (step :' and then the next 'is not None:'
start_idx = content.find("while (step :")
if start_idx != -1:
    end_idx = content.find("is not None:", start_idx)
    if end_idx != -1:
        # We want to replace the whole corrupted line and the line before it if needed
        # but let's just replace from 'while (step :' up to 'is not None:\n'
        
        # Let's find the actual line boundaries
        line_start = content.rfind("\n", 0, start_idx) + 1
        line_end = content.find("\n", end_idx) + 1
        
        corrupted_block = content[line_start:line_end]
        print(f"Replacing block: {repr(corrupted_block)}")
        
        # Construct the replacement
        # We need to preserve the indentation of the original loop
        indent = content[line_start:start_idx]
        replacement = f"{indent}while (step := plan.get_next_step(completed_steps)) is not None:\n{indent}    attempt_index = int(step.step_id.split('_')[1]) - 1"
        
        content = content[:line_start] + replacement + content[line_end:]
        
        with open("D:/projetos/metaO/src/metao/control_plane.py", "w", encoding="utf-8") as f:
            f.write(content)
        print("Refactor fixed successfully")
    else:
        print("Could not find 'is not None:'")
else:
    print("Could not find 'while (step :'")
