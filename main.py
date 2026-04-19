from pathlib import Path
import json

def deep_merge(dict_a, dict_b):
    """
    Recursively merges dict_b into dict_a.
    """
    for key, value in dict_b.items():
        if key in dict_a and isinstance(dict_a[key], dict) and isinstance(value, dict):
            deep_merge(dict_a[key], value)
        else:
            dict_a[key] = value
    return dict_a

def merge_dirs(a, b, out, mode="overwrite"):
    path_a = Path(a)
    path_b = Path(b)
    path_out = Path(out)

    def get_content(p):
        return p.read_text(encoding='utf-8') if p.is_file() else ""

    def merge_logic(data_a, data_b, mode):
        if mode == "overwrite":
            return data_b if data_b else data_a
        
        elif mode == "append":
            return data_a + data_b
        
        elif mode == "json":
            try:
                # Load JSON or default to empty dict if string is empty
                obj_a = json.loads(data_a) if data_a.strip() else {}
                obj_b = json.loads(data_b) if data_b.strip() else {}
                
                # Perform the deep merge
                merged = deep_merge(obj_a, obj_b)
                return json.dumps(merged, indent=4)
            except json.JSONDecodeError:
                return "Error: Invalid JSON content encountered"
        
        return data_a

    # Determine processing scope
    if path_a.is_file() and path_b.is_file():
        result = merge_logic(get_content(path_a), get_content(path_b), mode)
        path_out.parent.mkdir(parents=True, exist_ok=True)
        path_out.write_text(result, encoding='utf-8')
    else:
        path_out.mkdir(parents=True, exist_ok=True)
        files_a = {f.name for f in path_a.iterdir()} if path_a.is_dir() else {path_a.name}
        files_b = {f.name for f in path_b.iterdir()} if path_b.is_dir() else {path_b.name}
        
        for filename in (files_a | files_b):
            file_a = path_a / filename if path_a.is_dir() else (path_a if path_a.name == filename else Path("/dev/null"))
            file_b = path_b / filename if path_b.is_dir() else (path_b if path_b.name == filename else Path("/dev/null"))
            
            content_a = get_content(file_a) if file_a.exists() else ""
            content_b = get_content(file_b) if file_b.exists() else ""
            
            result = merge_logic(content_a, content_b, mode)
            (path_out / filename).write_text(result, encoding='utf-8')

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

def resolve_patterns(base, patterns):
    base = Path(base)
    results = []

    for pattern in patterns:
        matches = list(base.glob(pattern))
        for m in matches:
            if m.is_file():
                results.append(m)

    return results

for key,val in data.items():
    if val.get("enable")==True or val.get("force",False)==True:
        data[key]["enable"]=True
        continue
    else:
        data[key]["enable"]=ask_mod_depend(key,val)

Path("build/assets/minecraft").mkdir(exist_ok=True,parents=True)

for key, val in data.items():
    if val["enable"]:        
        for fgroup in val["filegroups"]:
            dst_base = Path("build") if fgroup.get("root") else Path("build/assets/minecraft")
            src_base = Path("resourcepack") if fgroup.get("root") else Path("resourcepack/assets/minecraft")
            #files = resolve_patterns(src_base, fgroup["files"])
            mode = fgroup.get("merge", "overwrite")

            for src_ in fgroup["files"]:
                if isinstance(src_,str):
                    files_ = resolve_patterns(src_base,[src_])
                    files_3=[]
                    for file_2 in files_:
                        rel = file_2.relative_to(src_base)
                        target = (dst_base / rel).resolve()
                        files_3.append([file_2,target])
                if isinstance(src_,dict):
                    files_ = resolve_patterns(src_base,[src_["src"]])
                    files_3=[]
                    for file_2 in files_:
                        target = (dst_base / src_["dst"]).resolve()
                        files_3.append([file_2,target])  

                for a in files_3:

                    src = a[0]
                    target = a[1]

                    #if dst_base not in target.parents and target != dst_base:
                    #    raise RuntimeError(f"Unsafe path: {target}")

                    if target.exists():
                        if mode == "json":
                            a = target.read_text(encoding="utf-8")
                            b = src.read_text(encoding="utf-8")
                            target.write_text(jsonwrap(a, b), encoding="utf-8")
                        else:
                            merge_dirs(target, src, target, mode)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(src.read_bytes())