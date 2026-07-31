#!/usr/bin/env python3
"""合并同名同坐标的种子 Place。

根因(已写入 schema/place.yaml):category 里的 birthplace 把「人与地的关系」误当成
「地点的属性」。洛阳本是 capital,有人要拿它当籍贯便另建一个 birthplace 的洛阳 ——
于是每来一个人就多一个同名地点。实测 163 个 birthplace 地点中 149 个只被
person.birthplace 引用;53 组同名重复(洛阳6/长安4/沛县4/镇州4)皆源于此。

合并规则(保守):
- 仅并「同名 + 同坐标」者。坐标不同的(巨鹿/建州/涿郡)可能确非一地,留人工判,不动。
- 存者取引用数最多的那个;category 取其中最具体的(capital > garrison > battlefield
  > pass > city > region),birthplace 已废弃故永不入选。
- 别名归并:被并者的 name/aliases 并入存者 aliases,不丢检索入口。
- 描述不合并 —— 存者自有其描述;被并者的描述多是「某人籍贯」之类的关系陈述,
  该信息已由 person.birthplace 表达。

幂等:被并 id 不存在即跳过。
"""
import yaml, glob, re, sys, pathlib, collections

SPECIFICITY = ["capital", "garrison", "battlefield", "pass", "city", "region"]

pl, files = {}, {}
for f in glob.glob("data/entities/places/*.yaml"):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("type") == "Place" and not d["id"].startswith("pl_cbdb_"):
        pl[d["id"]] = d
        files[d["id"]] = f

# 引用计数:一次扫描抓出每个文件里的 pl_ token(逐 id 全文搜是平方级,曾跑超时)
TOK = re.compile(r"\bpl_[A-Za-z0-9_]+\b")
refs = collections.Counter()
for f in glob.glob("data/**/*.yaml", recursive=True):
    txt = open(f, encoding="utf-8").read()
    m = re.match(r"id:\s*(\S+)", txt)
    own = m.group(1) if m else None
    for tok in set(TOK.findall(txt)):
        if tok in pl and tok != own:
            refs[tok] += 1

# 同名 + 同坐标 才成组
groups = collections.defaultdict(list)
for i, d in pl.items():
    groups[(d.get("name"), d.get("latitude"), d.get("longitude"))].append(i)

rename = {}   # 被并 -> 存者
keepers = []
for (name, lat, lng), ids in groups.items():
    if len(ids) < 2 or lat is None:
        continue
    # 存者:引用最多;并列则取 id 最短(通常是最早的规范 id)
    keep = sorted(ids, key=lambda i: (-refs[i], len(i)))[0]
    keepers.append(keep)
    for i in ids:
        if i != keep:
            rename[i] = keep

if not rename:
    print("无同名同坐标的重复,无事可做")
    sys.exit(0)

# 合并 category 与 aliases 到存者
for keep in set(keepers):
    merged = [i for i, k in rename.items() if k == keep]
    d = pl[keep]
    cats = [pl[i].get("category") for i in merged + [keep]]
    cats = [c for c in cats if c in SPECIFICITY]
    if cats:
        d["category"] = min(cats, key=lambda c: SPECIFICITY.index(c))
    elif d.get("category") == "birthplace":
        d["category"] = "city"          # birthplace 已废弃,无更具体者则退为 city
    al = list(d.get("aliases") or [])
    for i in merged:
        for a in [pl[i].get("name")] + list(pl[i].get("aliases") or []):
            if a and a != d.get("name") and a not in al:
                al.append(a)
    if al:
        d["aliases"] = al
    yaml.safe_dump(d, open(files[keep], "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False)

# 先删被并文件,再全库重指(否则会把待删文件里的自身 id 也改了)
for i in rename:
    pathlib.Path(files[i]).unlink(missing_ok=True)

n_files = 0
for f in glob.glob("data/**/*.yaml", recursive=True):
    p = pathlib.Path(f)
    s = old = p.read_text(encoding="utf-8")
    for src, dst in rename.items():
        s = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(src)}(?![A-Za-z0-9_])", dst, s)
    if s != old:
        p.write_text(s, encoding="utf-8"); n_files += 1

# 独有的 birthplace 残留(未成组者)也一并退档 —— 该值已从 schema 删除
n_bp = 0
for i, d in pl.items():
    if i in rename or d.get("category") != "birthplace":
        continue
    d["category"] = "city"
    yaml.safe_dump(d, open(files[i], "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False)
    n_bp += 1

print(f"合并 {len(rename)} 个重复地点 → {len(set(keepers))} 个存者;"
      f"重指 {n_files} 个文件;另有 {n_bp} 个未成组的 birthplace 退为 city")
