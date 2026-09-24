with open("D:/projetos/metaO/src/metao/control_plane.py", "r", encoding="utf-8") as f:
    content = f.read()

old_text = "while (step :\n          attempt_index = int(step.step_id.split('_')[1]) - 1= plan.get_next_step(completed_steps)) is not None:"
new_text = "while (step := plan.get_next_step(completed_steps)) is not None:\n        attempt_index = int(step.step_id.split('_')[1]) - 1"

if old_text in content:
    content = content.replace(old_text, new_text)
    with open("D:/projetos/metaO/src/metao/control_plane.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully replaced")
else:
    print("Old text not found. Printing corrupted snippet for debugging:")
    start = content.find("while (step :")
    if start != -1:
        print(content[start:start+200])
    else:
        print("Could not find 'while (step :'")
