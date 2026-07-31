#!/usr/bin/env python3
"""合并 2 组重复 Faction + 修 1 个错误 id 前缀 + 修 1 处人名笔误。

重复的两组是近乎逐字的复制:「晚唐宦官集团」(f_eunuch_tang 750-905 vs
f_late_tang_eunuchs 758-903)、「河朔三镇」(f_heshuo vs f_heshuo_3_zhen,起止全同,
只是 core_region 一个填 pl_hebei 一个填 pl_weizhou)。存者取起止更精确、成员更全者,
另一条的成员与描述并进来。

另:p_yangwu_group 是个 Faction 却挂着 p_ 前缀(p_ 是 Person 的前缀),改为 f_yangwu_group。
另:义社十兄弟的「韩重斌」是「韩重赟」之误(宋史·韩重赟传)。
"""
import yaml, glob, re, pathlib, sys

# 存者 ← 被并。存者取描述更详（列全「四贵」谱系）/ core_region 更准者。
MERGE = {
    "f_late_tang_eunuchs": "f_eunuch_tang",   # 存者 f_eunuch_tang,后者描述更细但起止较糙
    "f_heshuo_3_zhen":     "f_heshuo",        # 河朔三镇治所在魏州,但三镇跨河北,pl_hebei 更准
}
ID_FIX = {"p_yangwu_group": "f_yangwu_group"}   # Faction 不该用 p_ 前缀
NAME_FIX = {"韩重斌": "韩重赟"}                  # 宋史·韩重赟传

files, ents = {}, {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"):
        ents[d["id"]] = d; files[d["id"]] = f

for bad, good in MERGE.items():
    if bad not in ents: sys.exit(f"✗ 被并者不存在:{bad}")
    if good not in ents: sys.exit(f"✗ 存者不存在:{good}")
    if ents[bad].get("name") != ents[good].get("name"):
        sys.exit(f"✗ 拒绝合并异名 Faction:{ents[bad].get('name')} vs {ents[good].get('name')}")
for bad in ID_FIX:
    if bad not in ents: sys.exit(f"✗ 待改 id 不存在:{bad}")

# 合并:成员取并集,被并者的描述若更长则并入 significance 之后不做——只并成员与 sources,
# 描述以存者为准(两份描述说的是同一件事,拼起来只会重复)
for bad, good in MERGE.items():
    d, o = ents[good], ents[bad]
    for fld in ("core_members", "sources"):
        cur = list(d.get(fld) or [])
        for x in (o.get(fld) or []):
            if x not in cur: cur.append(x)
        if cur: d[fld] = cur
    yaml.safe_dump(d, open(files[good], "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False, width=200)
    pathlib.Path(files[bad]).unlink(missing_ok=True)

# 改 id:先落盘新档、删旧档,再全库重指
for bad, good in ID_FIX.items():
    d = ents[bad]; d["id"] = good
    new = f"data/entities/factions/{good.split('_',1)[1]}.yaml"
    yaml.safe_dump(d, open(new, "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False, width=200)
    if pathlib.Path(files[bad]).resolve() != pathlib.Path(new).resolve():
        pathlib.Path(files[bad]).unlink(missing_ok=True)

rename = {**MERGE, **ID_FIX}
n = 0
for f in glob.glob("data/**/*.yaml", recursive=True):
    p = pathlib.Path(f); s = old = p.read_text(encoding="utf-8")
    for src, dst in rename.items():
        s = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(src)}(?![A-Za-z0-9_])", dst, s)
    for src, dst in NAME_FIX.items():
        s = s.replace(src, dst)
    if s != old: p.write_text(s, encoding="utf-8"); n += 1

print(f"合并 {len(MERGE)} 组重复 Faction;改 {len(ID_FIX)} 个错误 id 前缀;"
      f"修 {len(NAME_FIX)} 处人名笔误;重指 {n} 个文件")
