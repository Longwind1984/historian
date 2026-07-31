#!/usr/bin/env python3
"""把 includes(Dynasty → Polity)填全,并声明 Person.dynasty_ref。

问题:朝代归属靠「年份落在哪个 Dynasty 的 [founded, ended] 区间」来算,而 19 个
Dynasty 的区间既重叠又有空档:

  辽 916~1125 与 宋 960~1279 重叠 165 年 —— 因为它俩本来就并存。
  匹配逻辑是「按 founded 升序取首个命中」,辽(916) 排在 宋(960) 前面,
  于是 960~1125 出生的人全被判成辽人 —— 实测「辽」分到 748 人,
  是最大的一档,超过唐(553)和宋(427)。而这库里真正的辽人只有 32 个。
  另有 13 人落在空档(如 1234 金亡~1271 元立)而无朝代。

根子在于:1050 年的人是辽是宋,取决于他在哪,不取决于他在何时。年份判不了。

数据里本来就有答案:4804 个人物带 dynasty_ref,指向其实际政权(北宋 2611、
唐 1333、明 467、清 131、元 96、契丹/辽 32)。但该字段从未在 schema 里声明,
所以不受校验(已有 21 处悬空),也没人拿它来算归属。

本脚本:
  1. schema/person.yaml 声明 dynasty_ref: ref → Polity
  2. 修 21 处悬空 dynasty_ref
  3. includes 填全:每个 Polity 归入其所属 Dynasty(14 条 → 84 条),
     使 Polity → Dynasty 成为查表而非猜测
配套的归属逻辑改写见 backend/app/api/links.py。
"""
import yaml, glob, pathlib, sys, collections

# Polity → Dynasty。依据是该政权属于哪个断代,不是「谁是正统」——
# 并存政权(辽/金/西夏/北汉)各归其本朝,不塞给宋。
D = {
  "d_xia":    ["k_xia"],
  "d_shang":  ["k_shang"],
  "d_zhou":   ["k_xizhou","k_dongzhou","k_qi_state","k_yan_state","k_lu_state","k_song_state",
               "k_jin_state","k_chu_state","k_zheng_state","k_qin_state","k_yue_state",
               "k_wu_state","k_han_state","k_wei_state","k_zhao_state"],
  "d_qin":    ["k_qin"],
  "d_han":    ["k_chu_xiang","k_xihan","k_xin","k_donghan","k_xiongnu",
               "k_yuanshao_pre","k_caowei_pre","k_shuhan_pre","k_dongwu_pre"],
  "d_sanguo": ["k_caowei","k_shuhan","k_dongwu"],
  "d_jin":    ["k_xijin","k_dongjin","k_hanzhao","k_houzhao","k_qian_qin","k_ranwei","k_houqin"],
  "d_nanbeichao": ["k_nanbeichao","k_beiwei","k_liusong","k_nan_qi","k_nan_liang",
                   "k_dong_wei","k_xi_wei","k_bei_qi","k_bei_zhou","k_nan_chen"],
  "d_sui":    ["k_sui"],
  "d_tang":   ["k_tang","k_wu_zhou"],
  "d_wudai":  ["k_yangwu","k_chu","k_houliang","k_qianshu","k_wuyue","k_min","k_nanhan",
               "k_houdong","k_jingnan","k_houshu","k_houjin","k_nantang","k_houhan",
               "k_beihan","k_houzhou"],
  "d_liao":   ["k_liao"],
  "d_song":   ["k_song","k_beisong","k_nansong","k_xixia"],
  "d_jin_jurchen": ["k_jin"],
  "d_yuan":   ["k_yuan","k_wu_zhu","k_han_chen"],
  "d_ming":   ["k_ming","k_waci","k_houjin_qing","k_dashun_li"],
  "d_qing":   ["k_qing","k_taiping","k_britain","k_riben"],
  "d_minguo": ["k_minguo"],
  "d_prc":    ["k_prc"],
}
# 说明几处易被质疑的归属:
#   k_xiongnu → d_han:匈奴(前209~48)与两汉相始终,断代上属汉。
#   k_xixia   → d_song:西夏(1038~1227)与宋并存,库中无「西夏」Dynasty,归宋断代。
#   k_britain / k_riben → d_qing:此二者是清季对手方,列入清断代仅为索引可达,
#     非谓其属中国朝代。它们无 territory,不上时间轴地图(见 2026-07-16 WORKLOG)。
#   k_waci    → d_ming:瓦剌(1438~1454)与明并存。
#   k_nanbeichao 是「时期」被误建成 Polity,与 d_nanbeichao 重复 —— 暂归其本朝代,
#     该不该留作 Polity 是单独的问题(见 WORKLOG 未尽事项)。

# 悬空的 dynasty_ref → 实存政权
DREF_FIX = {
  "k_wudai":    "d_wudai",     # 五代十国是断代不是政权,该指 Dynasty —— 但字段声明 to: Polity,
                               # 故此 13 人改为不设(见下方 DROP)
  "k_houtang":  "k_houdong",   # 后唐的真实 id
  "k_zhou_wu":  "k_wu_zhou",   # 武周,本轮刚改的前缀
  "k_liu_song": "k_liusong",   # 刘宋
  "k_ma_chu":   "k_chu",       # 楚(马楚)
}
DROP = {"k_wudai"}   # 指向断代而非政权者,删字段而非硬指一个政权

files, ents = {}, {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"): ents[d["id"]] = d; files[d["id"]] = f

# ── 护栏:覆盖必须完整,目标必须存在 ──
for did, pids in D.items():
    if did not in ents or ents[did].get("type") != "Dynasty": sys.exit(f"✗ 不是 Dynasty:{did}")
    for p in pids:
        if p not in ents: sys.exit(f"✗ Polity 不存在:{p}(在 {did} 下)")
        if ents[p].get("type") != "Polity": sys.exit(f"✗ 不是 Polity:{p}")
allp = {i for i, d in ents.items() if d.get("type") == "Polity"}
mapped = {p for v in D.values() for p in v}
if allp - mapped: sys.exit(f"✗ 有 Polity 未归入任何 Dynasty:{sorted(allp - mapped)}")
if mapped - allp: sys.exit(f"✗ 映射里有不存在的 Polity:{sorted(mapped - allp)}")
dup = [p for p, n in collections.Counter(p for v in D.values() for p in v).items() if n > 1]
if dup: sys.exit(f"✗ 同一 Polity 归入多个 Dynasty:{dup}")
for bad, good in DREF_FIX.items():
    if bad in DROP: continue
    if good not in ents: sys.exit(f"✗ dynasty_ref 改指目标不存在:{good}")

# ── 1. schema 声明 dynasty_ref ──
sp = pathlib.Path("schema/person.yaml"); s = sp.read_text(encoding="utf-8")
if "dynasty_ref" not in s:
    old = """  birthplace:
    type: ref"""
    assert old in s
    s = s.replace(old, """  dynasty_ref:
    # 人物的朝代归属,值是其所属**政权**(北宋/唐/明…),不是 Dynasty —— 名字有误导性,
    # 但 4804 个人物在用,改名的代价大于收益。此前从未在此声明,故不受校验,
    # 悬空了 21 处也没人知道。它是朝代归属的权威来源:年份判不了 1050 年的人是辽是宋
    # (那取决于他在哪),dynasty_ref 能。
    type: ref
    to: Polity
    optional: true
    label: 朝代归属(政权)
  birthplace:
    type: ref""")
    sp.write_text(s, encoding="utf-8")

# ── 2. 修悬空 dynasty_ref ──
n_fix = 0
for i, d in ents.items():
    r = d.get("dynasty_ref")
    if r is None or r in ents: continue
    if r in DROP:
        d.pop("dynasty_ref")
    elif r in DREF_FIX:
        d["dynasty_ref"] = DREF_FIX[r]
    else:
        sys.exit(f"✗ 未预料的悬空 dynasty_ref:{i} → {r}")
    yaml.safe_dump(d, open(files[i], "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False, width=200)
    n_fix += 1

# ── 3. 重建 includes ──
OUT = "data/relations/dynasty_includes.yaml"
old_inc = collections.defaultdict(set)
for f in glob.glob("data/relations/*.yaml"):
    if f.endswith("dynasty_includes.yaml"): continue
    rs = yaml.safe_load(open(f, encoding="utf-8")) or []
    keep = [r for r in rs if not (isinstance(r, dict) and r.get("type") == "includes"
                                  and str(r.get("from","")).startswith("d_"))]
    for r in rs:
        if isinstance(r, dict) and r.get("type") == "includes" and str(r.get("from","")).startswith("d_"):
            old_inc[r["from"]].add(r["to"])
    if len(keep) != len(rs):   # 旧的 Dynasty→Polity includes 移到新文件,避免两处维护
        yaml.safe_dump(keep, open(f, "w", encoding="utf-8"), allow_unicode=True,
                       sort_keys=False, default_flow_style=False, width=200)

rels = []
for did, pids in D.items():
    dn = ents[did].get("name")
    for p in pids:
        rels.append({"from": did, "to": p, "type": "includes",
                     "note": f"{ents[p].get('name')} 属{dn}断代"})
pathlib.Path(OUT).write_text(
    "# Dynasty → Polity 的断代归属(2026-07-16 填全:14 条 → %d 条)。\n"
    "# 在此之前只填了 9 个朝代,系统只能靠「年份落在哪个朝代区间」猜归属,而区间彼此\n"
    "# 重叠(辽 916~1125 与宋 960~1279 并存)—— 首个命中即返回的匹配把 960~1125 出生的人\n"
    "# 全判成辽人,「辽」因此分到 748 人,而真辽人只有 32 个。\n"
    "# 归属依据是断代,不是正统:辽/金/西夏/北汉各归其本朝,不塞给宋。\n" % len(rels)
    + yaml.safe_dump(rels, allow_unicode=True, sort_keys=False, default_flow_style=False, width=200),
    encoding="utf-8")
print(f"includes {sum(len(v) for v in old_inc.values())} → {len(rels)} 条;"
      f"修 {n_fix} 处悬空 dynasty_ref;schema 已声明 dynasty_ref")
