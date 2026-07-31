#!/usr/bin/env python3
"""事件分类第二轮:补 prosperity、给 41 个 Battle 实体归类、修上轮重扫漏掉的错分类。

背景:上一轮重扫只覆盖了手工列进映射表的 91/198 条。族色一上轴,剩下 107 条里的
错分类立刻显形——贞观之治/开元盛世等 6 条治世标着 reform(变法),事实性错误。
教训:重扫必须全量过一遍,不能只改"我想到的那些"。

幂等:按 name 匹配,只在 category 不同时写。
"""
import yaml, glob, sys

# ── Event:修正上轮漏掉/错判的 ──
EVENT = {
    # 治世·盛世:新增第 18 类(Rick 2026-07-15 拍板)。此前全塞在 reform,
    # 但贞观之治不是变法——是一段时代状态。
    "文景之治": "prosperity", "光武中兴": "prosperity", "开皇之治": "prosperity",
    "贞观之治": "prosperity", "开元盛世": "prosperity", "大中之治": "prosperity",
    # 终点是禅代,与 杨坚代周/朱温代唐/王莽篡汉 同构
    "司马氏代魏": "succession",
    # 异族陷都、俘帝、王朝亡——与 靖康之变(conquest) 同构
    "永嘉之乱": "conquest",
    # 十三年间平西川/镇海/淮西/平卢多役,与 平定三藩(war) 同构;"削藩"是目的不是形态
    "元和削藩": "war",
    # 核心事实是尽诛宦官(除黄衣 30 人),终结百年宦官专权 = 清洗
    "崔胤引朱温入京": "purge",
    # 归附/纳土/易帜 归 territory,与 张义潮归唐、吴越纳土归宋 同构。
    # 二者原标 diplomacy,但都是内部归附,不是外交。
    "朱温降唐": "territory", "东北易帜": "territory",
    # rebellion=民变·起义(印章「民」)只装民众起事。以下 5 条是军政集团内战:
    # 安史(节度使)、七国(诸侯王)、侯景(降将)、二次革命/护国(都督将领起兵)。
    # 与已归 war 的 八王之乱(皇族混战)、靖难之役(藩王起兵) 同构 → war(印章「兵」)。
    # 给安禄山盖「民」章是错的;而「亂」是治者视角,同样不用。
    # 六镇之乱 保留 rebellion:军户是被贬的世袭贱籍,其起事确属民变。
    # 庞勋之变 保留:桂林戍卒起事,与大泽乡(戍卒陈胜吴广)同构。
    "七国之乱": "war", "安史之乱": "war", "侯景之乱": "war",
    "二次革命": "war", "护国运动": "war",
}

# ── Battle:41 个实体本无 category 字段,前端只能一律回落成 battle(戰)。
#    军事族 4 类同枚举(见 schema/battle.yaml)。
BATTLE = {
    # 灭国:一方政权就此终结
    "鸣条之战": "conquest",             # 夏亡
    "牧野之战": "conquest",             # 商亡
    "南唐灭闽之战(建州之战)": "conquest",   # 闽亡
    "南唐灭楚之战(潭州之战)": "conquest",   # 楚亡
    "契丹灭后晋": "conquest",
    "宋平荆南": "conquest", "宋灭后蜀": "conquest", "宋灭南汉": "conquest",
    "宋灭南唐": "conquest", "宋灭北汉": "conquest",
    "蔡州之战(金亡)": "conquest",
    "崖山海战": "conquest",             # 南宋亡
    # 战争:跨年多役
    "夹河之战": "war",                  # 917-923 晋梁六年拉锯
    "后周攻南唐": "war",                # 955-958 三征
    "后周北伐辽": "war",                # 水陆并进连下三州三关
    "雍熙北伐": "war",                  # 三路伐辽,岐沟关/陈家谷分头成役
    # 战役:单次
    "泓水之战": "battle", "城濮之战": "battle", "桂陵之战": "battle", "马陵之战": "battle",
    "长平之战": "battle", "潞州之战": "battle", "柏乡之战": "battle",
    "幽州之战(幽州保卫战)": "battle", "阳城之战(白团卫村之战)": "battle",
    "高平之战": "battle", "六合之战": "battle", "高梁河之战": "battle",
    "三川口之战": "battle", "好水川之战": "battle", "定川寨之战": "battle",
    "黄天荡之战": "battle", "郾城大捷": "battle", "襄樊之战": "battle",
    "鄱阳湖之战": "battle", "北京保卫战": "battle", "土木堡之变": "battle",
    "萨尔浒之战": "battle", "宁远之战": "battle", "山海关之战": "battle",
    "甲午海战(黄海)": "battle",
}

changed, seen = 0, set()
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if not isinstance(d, dict):
        continue
    t, nm = d.get("type"), d.get("name")
    M = EVENT if t == "Event" else BATTLE if t == "Battle" else None
    if M is None or nm not in M:
        continue
    seen.add((t, nm))
    if d.get("category") == M[nm]:
        continue
    # Battle 无 category 字段:插到 end_date 之后(与 schema 字段序一致)
    if "category" not in d:
        items = list(d.items())
        at = next((i for i, (k, _) in enumerate(items) if k == "end_date"), None)
        at = at + 1 if at is not None else next(i for i, (k, _) in enumerate(items) if k == "date") + 1
        items.insert(at, ("category", M[nm]))
        d = dict(items)
    else:
        d["category"] = M[nm]
    yaml.safe_dump(d, open(f, "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False)
    changed += 1

miss = [f"{t}:{n}" for t, M in (("Event", EVENT), ("Battle", BATTLE)) for n in M if (t, n) not in seen]
print(f"改类 {changed} 条  (Event 映射 {len(EVENT)} 条 / Battle 映射 {len(BATTLE)} 条)")
if miss:
    print("!! 映射中未匹配到实体(名字对不上):", miss)
    sys.exit(1)
