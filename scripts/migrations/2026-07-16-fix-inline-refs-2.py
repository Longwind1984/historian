#!/usr/bin/env python3
"""补掉首轮遗漏的 4 处内嵌外键 + 1 处历法口径不一致。

前一个脚本(2026-07-16-fix-inline-refs.py)漏了两条改指(p_yanghao_ming / d_ming),
另有两处需按语境分别裁定 —— 同一个 k_yuan_pre,在鄱阳湖之战里元不是交战方(该删),
在红巾军起义里元正是被反的对象(该指 k_yuan)。故不能一刀切改名,拆开处理。
"""
import yaml, glob, sys

RENAME = {
    "p_yanghao_ming": "p_yanghao",   # 萨尔浒之战主帅,新建人物用规范 id
    "d_ming":         "k_ming",      # 类型不符:声明 to: Polity,值是 Dynasty
}
FACTUAL = {
    # 红巾军起义(1351)反的就是元 —— 与鄱阳湖之战(1363,朱元璋灭陈友谅,元不在场)不同,
    # 同一个坏 id 在两处语境不同,故分开裁。
    ("e_hongjinjun_qiyi", "polities_involved"): ("k_yuan_pre", "k_yuan"),
    # 李从珂随后唐灭亡自焚,是同一件事:后唐 ended = {936,11}(农历口径,清泰三年闰十一月),
    # 而其卒年被记为 {937,1}(公历换算) —— 于是人比其政权多活两月。全库政权链
    # (后汉 951-01 → 后周 951-02)用的都是农历口径,故统一到 936-11。
    # 农历/公历口径在库中仍有混用,是更大的一致性问题,见 WORKLOG。
    ("p_licongke", "died"): ({"year": 937, "month": 1}, {"year": 936, "month": 11}),
}

files, ents = {}, {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"):
        ents[d["id"]] = d; files[d["id"]] = f

for bad, good in RENAME.items():
    if good not in ents: sys.exit(f"✗ 改指目标不存在:{good}")
for (eid, fld), (_, good) in FACTUAL.items():
    if eid not in ents: sys.exit(f"✗ 实体不存在:{eid}")
    if isinstance(good, str) and good not in ents: sys.exit(f"✗ 目标不存在:{good}")

schemas = {}
for f in glob.glob("schema/*.yaml"):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("type") and "fields" in d:
        r = {}
        for k, v in (d["fields"] or {}).items():
            if not isinstance(v, dict): continue
            if v.get("type") == "ref" and v.get("to"): r[k] = True
            elif v.get("type") == "array" and isinstance(v.get("items"), dict) \
                 and v["items"].get("type") == "ref": r[k] = False
        schemas[d["type"]] = r

n = 0
for i, d in ents.items():
    ch = False
    for fld, is_scalar in schemas.get(d.get("type"), {}).items():
        if d.get(fld) is None: continue
        if is_scalar and d[fld] in RENAME: d[fld] = RENAME[d[fld]]; ch = True
        elif not is_scalar and isinstance(d[fld], list):
            out = [RENAME.get(x, x) if isinstance(x, str) else x for x in d[fld]]
            if out != d[fld]: d[fld] = out; ch = True
    for (eid, fld), (bad, good) in FACTUAL.items():
        if i != eid or fld not in d: continue
        if isinstance(d[fld], list) and bad in d[fld]:
            d[fld] = [good if x == bad else x for x in d[fld]]; ch = True
        elif d[fld] == bad:
            d[fld] = good; ch = True
    if ch:
        yaml.safe_dump(d, open(files[i], "w", encoding="utf-8"), allow_unicode=True,
                       sort_keys=False, default_flow_style=False, width=200); n += 1
print(f"修正 {n} 个实体")
