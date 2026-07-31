#!/usr/bin/env python3
"""合并 23 组重复的种子人物。

成因:两批导入各写各的,id 约定还不同(p_liu_chong vs p_liuchong)。模式极整齐 ——
每组必是「一条有 reign_start/end、无月份」+「一条有卒月、无在位年」,且全是
五代十国/辽/金 君主。前者供帝王轴,后者供生卒;谁也不知道对方存在。

故合并取并集,不是二选一:存者缺的字段从被并者补进来。年份冲突(如李从珂
卒 936 vs 937-01,系农历年与公历换算之差)不自动裁,打印出来人工看。

另一组不同名但同人:徐知诰 = 李昪(937 代吴建齐,939 复姓李改国号唐),互为 alias。
存者取 p_li_bian —— 他以李昪之名而终,且该条带 roles:emperor + reign,是帝王轴所需。

幂等:被并 id 不存在即跳过。
"""
import yaml, glob, re, pathlib, collections, sys

# 不同名但同人,须手工裁定(同名组由下方自动成组)
MANUAL = {"p_xuzhigao": "p_li_bian"}

files, ents = {}, {}
for f in glob.glob("data/entities/persons/*.yaml"):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"):
        ents[d["id"]] = d; files[d["id"]] = f

# 引用计数:一次全扫,别逐 id 搜(平方级)
TOK = re.compile(r"\bp_[A-Za-z0-9_]+\b")
refs = collections.Counter()
for f in glob.glob("data/**/*.yaml", recursive=True):
    txt = open(f, encoding="utf-8").read()
    m = re.match(r"id:\s*(\S+)", txt)
    own = m.group(1) if m else None
    for tok in set(TOK.findall(txt)):
        if tok in ents and tok != own: refs[tok] += 1

# 成组:同名的种子人物(cbdb 桩不参与 —— 那是另一个量级的去重问题)
groups = collections.defaultdict(list)
for i, d in ents.items():
    if not i.startswith("p_cbdb_"): groups[d.get("name")].append(i)

rename = {}
for name, ids in groups.items():
    if len(ids) < 2: continue
    keep = sorted(ids, key=lambda i: (-refs[i], len(i)))[0]
    for i in ids:
        if i != keep: rename[i] = keep
for bad, good in MANUAL.items():
    if bad in ents and good in ents: rename[bad] = good

if not rename:
    print("无重复人物,无事可做"); sys.exit(0)
for bad, good in rename.items():
    if good not in ents: sys.exit(f"✗ 存者不存在:{good}")

def prec(v):
    """年月精度:有 month 者更精确"""
    return isinstance(v, dict) and v.get("month") is not None

SCALARS = ["courtesy_name","art_name","born","died","floruit_start","floruit_end",
           "reign_start","reign_end","gender","importance","birthplace","image","bio"]
LISTS   = ["alias","roles","sources"]

conflicts = []
merged_into = collections.defaultdict(list)
for bad, good in rename.items(): merged_into[good].append(bad)

for keep, bads in merged_into.items():
    d = ents[keep]
    for bad in bads:
        o = ents[bad]
        for f in SCALARS:
            if o.get(f) is None: continue
            if d.get(f) is None:
                d[f] = o[f]                       # 存者缺 → 直接补
            elif d[f] != o[f]:
                yk, yo = (d[f].get("year") if isinstance(d[f], dict) else None,
                          o[f].get("year")  if isinstance(o[f], dict) else None)
                if yk is not None and yk == yo and prec(o[f]) and not prec(d[f]):
                    d[f] = o[f]                   # 同年,被并者有月份 → 取更精确者
                elif yk is not None and yo is not None and yk != yo:
                    conflicts.append(f"{d.get('name')}({keep}).{f}: 存者 {d[f]} vs 被并 {o[f]}")
        for f in LISTS:
            cur = list(d.get(f) or [])
            for x in (o.get(f) or []):
                if x not in cur: cur.append(x)
            if cur: d[f] = cur
        # 被并者的名字进 alias,不丢检索入口
        if o.get("name") and o["name"] != d.get("name"):
            al = list(d.get("alias") or [])
            if o["name"] not in al: al.append(o["name"]); d["alias"] = al
        if isinstance(o.get("ext"), dict):
            d["ext"] = {**o["ext"], **(d.get("ext") or {})}
    d["alias"] = [a for a in (d.get("alias") or []) if a != d.get("name")] or None
    if d["alias"] is None: d.pop("alias")
    yaml.safe_dump(d, open(files[keep], "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False, width=200)

# 先删被并文件,再重指(否则会把待删文件里的自身 id 也改了)
for i in rename: pathlib.Path(files[i]).unlink(missing_ok=True)
n = 0
for f in glob.glob("data/**/*.yaml", recursive=True):
    p = pathlib.Path(f); s = old = p.read_text(encoding="utf-8")
    for src, dst in rename.items():
        s = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(src)}(?![A-Za-z0-9_])", dst, s)
    if s != old: p.write_text(s, encoding="utf-8"); n += 1

print(f"合并 {len(rename)} 个重复人物 → {len(merged_into)} 个存者;重指 {n} 个文件")
if conflicts:
    print(f"⚠ 年份冲突 {len(conflicts)} 处,已保留存者的值,需人工核:")
    for c in conflicts: print("   ", c)
