from github import Github
import re, ast

import os
TOKEN = os.environ.get("GITHUB_TOKEN")

#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
ORG_NAME = "TASKAHG"


g = Github(TOKEN)
org = g.get_organization(ORG_NAME)

# Regex tìm tên bảng sau FROM, JOIN, INTO, UPDATE, TABLE
pattern = re.compile(r"(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z0-9_\.{}]+)")

# Lấy biến hằng từ file Python
def extract_vars(content):
    vars_map = {}
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if all(isinstance(t, ast.Name) for t in node.targets) and isinstance(node.value, ast.Constant):
                    for t in node.targets: vars_map[t.id] = node.value.value
                elif len(node.targets) == 1 and isinstance(node.targets[0], ast.Tuple) and isinstance(node.value, ast.Tuple):
                    for n, v in zip(node.targets[0].elts, node.value.elts):
                        if isinstance(n, ast.Name) and isinstance(v, ast.Constant):
                            vars_map[n.id] = v.value
    except: pass
    return vars_map

# Tạo map biến -> giá trị cho repo
def build_var_map(repo):
    vars_map = {}
    try:
        stack = [repo.get_contents("")]
        while stack:
            contents = stack.pop()
            for c in contents:
                if c.type == "dir": stack.append(repo.get_contents(c.path))
                elif c.path.endswith(".py") and not c.path.endswith("scanning.py"):
                    try: vars_map.update(extract_vars(c.decoded_content.decode(errors='ignore')))
                    except: pass
    except: pass
    return vars_map

# Quét repo lấy tên bảng
def scan_tables(repo):
    tables = set()
    vars_map = build_var_map(repo)
    def traverse(contents):
        for c in contents:
            if c.type == "dir": traverse(repo.get_contents(c.path))
            elif c.path.endswith(".py") and not c.path.endswith("Scanning.py"):
                try:
                    content = c.decoded_content.decode(errors='ignore')
                    for tbl in pattern.findall(content):
                        while '{' in tbl and '}' in tbl:
                            var_name = tbl.split('{')[1].split('}')[0]
                            if var_name in vars_map: tbl = tbl.replace(f"{{{var_name}}}", vars_map[var_name])
                            else: break
                        tables.add(tbl)
                except: pass
    try: traverse(repo.get_contents(""))
    except: pass
    for t in sorted(tables): print(t)

# Quét tất cả repo trong org
for r in org.get_repos(): scan_tables(r)
