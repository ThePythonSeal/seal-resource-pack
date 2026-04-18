from pathlib import Path
import json


def merge_dirs(dir_a, dir_b, output_dir, mode="overwrite"):
    dir_a = Path(dir_a).resolve()
    dir_b = Path(dir_b).resolve()
    out = Path(output_dir).resolve()

    out.mkdir(parents=True, exist_ok=True)

    if mode not in {"overwrite", "append", "insert"}:
        raise ValueError("Invalid mode")

    def is_binary(path):
        with path.open("rb") as f:
            return b"\x00" in f.read(4096)

    def read_text(p):
        return p.read_text(encoding="utf-8")

    def write_text(p, data):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(data, encoding="utf-8")

    def copy_binary(src, dst):
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())

    def merge_text(a, b):
        if mode == "overwrite":
            return b
        if mode == "append":
            return a + b
        if mode == "insert":
            marker = "%i"
            if marker in a:
                left, right = a.split(marker, 1)
                return left + b + marker + right
            return a + marker + b

    files_a = {p.relative_to(dir_a): p for p in dir_a.rglob("*") if p.is_file()}
    files_b = {p.relative_to(dir_b): p for p in dir_b.rglob("*") if p.is_file()}

    for rel in set(files_a) | set(files_b):
        a = files_a.get(rel)
        b = files_b.get(rel)

        target = (out / rel).resolve()

        # safety check: prevent escaping output dir
        if out not in target.parents and target != out:
            raise RuntimeError(f"Unsafe path detected: {target}")

        if a and b:
            if is_binary(a) or is_binary(b):
                copy_binary(b, target)
            else:
                write_text(target, merge_text(read_text(a), read_text(b)))

        elif b:
            if is_binary(b):
                copy_binary(b, target)
            else:
                write_text(target, read_text(b))

        else:
            if is_binary(a):
                copy_binary(a, target)
            else:
                write_text(target, read_text(a))

    return out

with open("modules.json", "r", encoding="utf-8") as f:
    data = json.load(f)

def ask_mod(name, default):
    while True:
        prompt = "Y/n" if default else "y/N"
        x = input(f"Enable {name} [{prompt}] ").strip().lower()

        if x == "":
            return default
        if x in {"y", "yes"}:
            return True
        if x in {"n", "no"}:
            return False

def ask_mod_depend(key,val):
    global data
    a=ask_mod(key,val["default"])
    for i in val["depends"]:
        if data[i].get("enable",None) != True:
            print(f"{key} needs {i} as a dependency")
            data[i]["enable"]=ask_mod_depend(i,data[i])
    return a
for key,val in data.items():
    if val.get("enable")==True:
        continue
    else:
        data[key]["enable"]=ask_mod_depend(key,val)

print(data)

Path("build/assets/minecraft").mkdir(exist_ok=True,parents=True)

for key,val in data.items():
    if val["enable"]:
        merge_dirs("build/assets/minecraft", "modules/"+key, "build/assets/minecraft", val.get("merge", "overwrite"))