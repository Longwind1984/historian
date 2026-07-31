#!/usr/bin/env python3
"""合并 2 组重复 Polity + 修 3 个 id 前缀与 type 不符。

前两轮查了重复地点、重复人物、重复 Faction,唯独没查过重复 Polity —— 又一个
「某个方向没人查过」。查了就有:

- 北周 两条(d_zhou_north / k_bei_zhou),起止全同 557~581
- 陈   两条(k_chen / k_nan_chen),起止全同 557~589

id 前缀与 type 不符(前缀是靠 id 一眼认出类型的唯一凭据,错了就误导每一个读者):
- d_zhou_north 是 Polity 却挂 d_(Dynasty 的前缀) → 与合并一并消失
- d_zhou_wu    是 Polity(武周 690~705)却挂 d_ → k_wu_zhou
- e_beijing_bao_wei 是 Battle 却挂 e_(Event 的前缀) → b_beijing_bao_wei

存者取被引用更多者。字段取并集。
"""
import yaml, glob, re, pathlib, sys

MERGE = {"d_zhou_north": "k_bei_zhou",   # 存者被引 6 次 vs 2 次
         "k_chen":       "k_nan_chen"}   # 存者被引 2 次 vs 1 次
ID_FIX = {"d_zhou_wu": "k_wu_zhou", "e_beijing_bao_wei": "b_beijing_bao_wei"}
DIRS = {"Polity": "polities", "Battle": "battles"}

files, ents = {}, {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"): ents[d["id"]] = d; files[d["id"]] = f

for bad, good in MERGE.items():
    for x in (bad, good):
        if x not in ents: sys.exit(f"✗ 不存在:{x}")
    if ents[bad].get("name") != ents[good].get("name"):
        sys.exit(f"✗ 拒绝合并异名:{ents[bad].get('name')} vs {ents[good].get('name')}")
    # 只比年份 —— 两条的差异正是精度(557 vs 557-01),比全等会把该合的挡在门外。
    # 年份不同才是真的不同政权,那种要拦。
    yr = lambda v: (v or {}).get("year")
    if yr(ents[bad].get("founded")) != yr(ents[good].get("founded")) \
       or yr(ents[bad].get("ended")) != yr(ents[good].get("ended")):
        sys.exit(f"✗ 拒绝合并起止年不同者:{bad} vs {good}")
for bad, good in ID_FIX.items():
    if bad not in ents: sys.exit(f"✗ 不存在:{bad}")
    if good in ents: sys.exit(f"✗ 新 id 已被占用:{good}")

def dump(d, p):
    yaml.safe_dump(d, open(p, "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False, width=200)

# 合并:存者缺什么就从被并者补什么;都有且不同则留存者
for bad, good in MERGE.items():
    d, o = ents[good], ents[bad]
    for k, v in o.items():
        if k in ("id", "type"): continue
        if d.get(k) is None:
            d[k] = v
        elif k in ("founded", "ended") and isinstance(v, dict) and isinstance(d[k], dict) \
                and v.get("year") == d[k].get("year") \
                and v.get("month") is not None and d[k].get("month") is None:
            d[k] = v          # 同年而被并者带月份 → 取更精确者
    dump(d, files[good])
    pathlib.Path(files[bad]).unlink(missing_ok=True)

# 改 id:落新档、删旧档
for bad, good in ID_FIX.items():
    d = ents[bad]; d["id"] = good
    new = f"data/entities/{DIRS[d['type']]}/{good.split('_',1)[1]}.yaml"
    dump(d, new)
    if pathlib.Path(files[bad]).resolve() != pathlib.Path(new).resolve():
        pathlib.Path(files[bad]).unlink(missing_ok=True)

rename = {**MERGE, **ID_FIX}
n = 0
for f in glob.glob("data/**/*.yaml", recursive=True):
    p = pathlib.Path(f); s = old = p.read_text(encoding="utf-8")
    for src, dst in rename.items():
        s = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(src)}(?![A-Za-z0-9_])", dst, s)
    if s != old: p.write_text(s, encoding="utf-8"); n += 1
print(f"合并 {len(MERGE)} 组重复 Polity;改 {len(ID_FIX)} 个错误前缀;重指 {n} 个文件")
