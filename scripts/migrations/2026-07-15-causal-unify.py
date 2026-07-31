#!/usr/bin/env python3
"""把 Event↔Event 因果统一到 led_to,清掉野生的 preceded_by。

背景:
- schema/relations.yaml 只定义了 led_to / caused_by 作为因果类型;preceded_by 仅在
  schema/dynasty.yaml 里给 Dynasty→Dynasty 用。但库里有 53 条 Event↔Event 的
  preceded_by,前端 deriveEventCausal 不认它 → 这 53 条因果对因果面板完全不可见。
- 更麻烦的是库里混了两套相反的约定:49 条按「from 导致 to」写(注释均为「A→B」),
  4 条按 preceded_by 的英文本义写(A is preceded by B = B 在前)。同名反义,必须收口。
- 另外 event_causal.yaml(21 led_to + 1 caused_by)是后写的、每条带考据 note 的因果层,
  与旧 preceded_by 有 14 条重复主张,其 note 明显更完整。

处置:重复的丢弃(留 event_causal 的)、方向反的按史实裁定、其余转 led_to。
Dynasty→ 的那条保留 preceded_by(正当用法)。

幂等:preceded_by 清完后复跑无事可做。
"""
import yaml, glob, re, sys, pathlib, collections

ent = {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"):
        ent[d["id"]] = (d.get("type"), d.get("name", ""))
name = lambda i: ent.get(i, ("?", "?" + i))[1]
etype = lambda i: ent.get(i, ("?", "?"))[0]

# ── 手工裁定(这 4 条按 preceded_by 英文本义写,与其余 49 条方向相反) ──
# 元和削藩←安史之乱、甘露之变←牛李党争 两条已被 event_causal 的 led_to 覆盖,
# 走下面的自动 DROP 分支,无需在此列出。
DROP_BAD = {
    ("e_qiguo_zhiluan", "e_wen_jing_zhizhi"):
        "七国之乱(-154)落在文景之治(-180~-141)区间内,是时段包含不是因果;"
        "note「稳定后休养生息」与 from→to 方向自相矛盾。七国之乱已有入边(楚汉战争→七国之乱)",
}
REVERSE = {   # (原from,原to) -> 理由;改写为 to→from 的 led_to
    ("e_zhou_reform", "e_shumiyuan"):
        "五代枢密院制度(907成型)在前,周世宗改革(955)在后。原记录按英文本义写,"
        "转 led_to 时须掉向,否则把「改革导致制度」这个反果为因固化下来",
}

# ── 既有因果主张(led_to / caused_by 归一成 "a 导致 b") ──
claims = {}
for f in glob.glob("data/relations/*.yaml"):
    for r in (yaml.safe_load(open(f, encoding="utf-8")) or []):
        if not isinstance(r, dict):
            continue
        if r.get("type") == "led_to":
            claims[(r["from"], r["to"])] = f.split("/")[-1]
        elif r.get("type") == "caused_by":
            claims[(r["to"], r["from"])] = f.split("/")[-1]

# ── 逐条定处置 ──
plan = collections.defaultdict(dict)     # file -> {(from,to): (action, why)}
hit_manual = set()
seen = set()
for f in sorted(glob.glob("data/relations/*.yaml")):
    fn = f.split("/")[-1]
    for r in (yaml.safe_load(open(f, encoding="utf-8")) or []):
        if not isinstance(r, dict) or r.get("type") != "preceded_by":
            continue
        k = (r["from"], r["to"])
        if etype(k[0]) == "Dynasty":
            plan[fn][k] = ("KEEP", "Dynasty→ 是 preceded_by 的正当用法")
        elif k in DROP_BAD:
            hit_manual.add(k); plan[fn][k] = ("DROP", DROP_BAD[k])
        elif k in REVERSE:
            hit_manual.add(k); plan[fn][k] = ("REVERSE", REVERSE[k])
        elif k in claims:
            plan[fn][k] = ("DROP", f"led_to/caused_by 已覆盖同一主张({claims[k]}),其 note 更完整")
        elif (k[1], k[0]) in claims:
            plan[fn][k] = ("DROP", f"方向与 {claims[(k[1],k[0])]} 的 led_to 相反;以考据过的 event_causal 为准")
        elif k in seen:
            plan[fn][k] = ("DROP", "同 from/to 的 preceded_by 重复")
        else:
            seen.add(k); plan[fn][k] = ("RETYPE", "转 led_to")

# 幂等:非 Dynasty 的 preceded_by 清完即无事可做(此时手工裁定的 key 本就不该再命中)
todo = [k for fn in plan for k, (a, _) in plan[fn].items() if a != "KEEP"]
if not todo:
    print("已完成:Event↔Event 的 preceded_by 已清空,无事可做")
    sys.exit(0)

# 护栏:仍有待处置条目时,手工裁定的 key 必须命中。上一版我凭记忆猜 id
# (e_zhoushizong_gaige / e_wenjing_zhizhi),全部对不上 → 裁定静默失效,
# 那两条反向链会被当普通条目转成 led_to,把「改革导致制度」这种反果为因固化下来。
missing = (set(DROP_BAD) | set(REVERSE)) - hit_manual
if missing:
    print("!! 手工裁定的 id 未命中任何记录,拒绝执行:", [(name(a), name(b)) for a, b in missing])
    sys.exit(1)

# ── 块级文本手术(不用 yaml 往返:8 个目标文件虽无注释,但整文件重排会淹掉真实改动) ──
BLOCK = re.compile(r"^- from: (\S+)\n((?:  .*\n|\n)*)", re.M)
tot = collections.Counter()
for f in sorted(glob.glob("data/relations/*.yaml")):
    fn = f.split("/")[-1]
    if fn not in plan:
        continue
    p = pathlib.Path(f)
    src = p.read_text(encoding="utf-8")
    out, pos = [], 0
    for m in BLOCK.finditer(src):
        frm, body = m.group(1), m.group(2)
        to_m = re.search(r"^  to: (\S+)$", body, re.M)
        is_pb = re.search(r"^  type: preceded_by$", body, re.M)
        k = (frm, to_m.group(1)) if to_m else None
        if not (is_pb and k in plan[fn]):
            continue
        act, _ = plan[fn][k]
        if act == "KEEP":
            continue
        out.append(src[pos:m.start()]); pos = m.end()
        if act == "RETYPE":
            out.append(m.group(0).replace("  type: preceded_by\n", "  type: led_to\n", 1))
        elif act == "REVERSE":
            blk = m.group(0).replace("  type: preceded_by\n", "  type: led_to\n", 1)
            blk = blk.replace(f"- from: {k[0]}\n", "- from: \x00\n", 1)
            blk = re.sub(r"^  to: \S+$", f"  to: {k[0]}", blk, count=1, flags=re.M)
            blk = blk.replace("- from: \x00\n", f"- from: {k[1]}\n", 1)
            out.append(blk)
        # DROP: 整块不写回
        tot[act] += 1
    out.append(src[pos:])
    p.write_text("".join(out), encoding="utf-8")

for fn in sorted(plan):
    for k, (act, why) in plan[fn].items():
        if act == "KEEP":
            tot["KEEP"] += 1
print(f"处置: {dict(tot)}")
print(f"  RETYPE=转 led_to / DROP=丢弃(重复或方向错) / REVERSE=掉向后转 led_to / KEEP=Dynasty 保留")
