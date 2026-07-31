import yaml, glob, re, sys
BC=re.compile(r'BC\d'); AD=re.compile(r'AD\d')
def txt(e): return ' '.join(str(e.get(k,'')) for k in ('bio','description','note','impact'))
YEAR_LINE=re.compile(r'^(\s*year:\s*)(\d+)(\s*)$')
apply = '--apply' in sys.argv

def negate_file(path, only_value=None):
    """把文件里所有 year: <正数> 改成负数(或仅指定 only_value)。返回改动条数。"""
    lines=open(path).read().split('\n'); changed=0; out=[]
    for ln in lines:
        m=YEAR_LINE.match(ln)
        if m and (only_value is None or int(m.group(2))==only_value):
            out.append(f"{m.group(1)}-{m.group(2)}{m.group(3)}"); changed+=1
        else:
            out.append(ln)
    if apply and changed: open(path,'w').write('\n'.join(out))
    return changed

targets=[]
# Persons: BC marker & no AD => fully BCE, negate all; 王莽 spanner => born(45) only
for f in glob.glob('data/entities/persons/*.yaml'):
    e=yaml.safe_load(open(f))
    if not isinstance(e,dict): continue
    t=txt(e)
    if BC.search(t):
        if AD.search(t):  # spanner (王莽)
            targets.append((f, e.get('name'), 45))  # 仅 born 45->-45
        else:
            targets.append((f, e.get('name'), None))
# Events: BC marker & no AD
for f in glob.glob('data/entities/events/*.yaml'):
    e=yaml.safe_load(open(f))
    if isinstance(e,dict) and BC.search(txt(e)) and not AD.search(txt(e)):
        targets.append((f, e.get('name'), None))
# Polities: 西楚/秦朝 negate positives; 西汉 EXCLUDE
for f in glob.glob('data/entities/polities/*.yaml'):
    e=yaml.safe_load(open(f))
    if not isinstance(e,dict): continue
    if e.get('id')=='k_xihan': continue  # ended 9 = AD9, 保持
    if BC.search(txt(e)):
        targets.append((f, e.get('name'), None))

total=0
for f,name,only in sorted(targets):
    c=negate_file(f, only)
    total+=c
    print(f"{'[APPLY]' if apply else '[DRY]'} {name:8} {f.split('/')[-1]:28} 改 {c} 个 year" + (f" (仅{only})" if only else ""))
print(f"\n{'已应用' if apply else 'DRY-RUN'} 目标 {len(targets)} 个实体, 共 {total} 个 year 取负")
