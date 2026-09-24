with open("D:/projetos/metaO/src/metao/control_plane.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "_state" in line:
            print(f"{i}: {line.strip()}")
