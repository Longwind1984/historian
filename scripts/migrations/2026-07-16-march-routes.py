#!/usr/bin/env python3
"""给史载起讫明确的战役补 march（行军路线），供地图画箭头。

Rick 第4件:「如果是某个军队在往某个方向进攻,那它应该是一个箭头」。
Battle/Event 原有 combatants/commanders,但无行军起讫 —— 没有数据而画箭头即是编造方向,
故先补数据再画。

只取起讫皆有可考地点、且行军方向本身是该役定性事实者。宁少勿滥:
官渡(袁绍自邺南下)、巨鹿(项羽渡漳)等因「邺」「漳水」尚无 Place 实体而暂缺。

幂等:已有 march 即跳过。
"""
import yaml, sys, glob, pathlib

# eid -> [(from_place, to_place, side_polity|None, note)]
MARCH = {
    "b_muye": [
        ("pl_haojing", "pl_muye", None,
         "周武王自镐京东出,会八百诸侯于孟津,进至牧野。《史记·周本纪》"),
    ],
    "e_chibi_zhizhan": [
        ("pl_jiangling_zhang", "pl_chibi", None,
         "曹操取江陵后顺江东下,与孙刘联军遇于赤壁。《三国志·武帝纪》"),
    ],
    "e_feishui_zhizhan": [
        ("pl_chang_an", "pl_shouchun_qin", None,
         "苻坚自长安发兵,主力趋寿阳,临淝水。《晋书·苻坚载记》"),
    ],
    # 明北伐本为「先取山东、旋师河南、下潼关、后进大都」四步,但「山东」「潼关」尚无
    # Place 实体。不为画箭头而编 id —— 只落两段有实体可依的:应天→汴梁(河南)→大都。
    "e_ming_beifa_dadu": [
        ("pl_nanjing_ming", "pl_kaifeng", None,
         "徐达自应天北伐,先取山东撤其屏蔽,旋师河南拔汴梁。《明史·太祖本纪》"),
        ("pl_kaifeng", "pl_dadu", None,
         "既下潼关守其户槛,而后进师大都。《明史·徐达传》"),
    ],
    "e_jingnan_zhiyi": [
        ("pl_beijing", "pl_nanjing_ming", None,
         "燕王朱棣自北平起兵,四年而下南京。《明史·成祖本纪》"),
    ],
}

byid = {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"):
        byid[d["id"]] = (f, d)

# 护栏:实体与其起讫地点必须都存在且有坐标,否则拒绝执行(别落一条画不出的数据)
bad = []
for eid, legs in MARCH.items():
    if eid not in byid:
        bad.append(f"事件不存在: {eid}"); continue
    for frm, to, _side, _n in legs:
        for p in (frm, to):
            if p not in byid:
                bad.append(f"{eid}: 地点不存在 {p}")
            elif byid[p][1].get("latitude") is None:
                bad.append(f"{eid}: 地点无坐标 {p}")
if bad:
    print("!! 拒绝执行:"); [print("   ", b) for b in bad]; sys.exit(1)

n = 0
for eid, legs in MARCH.items():
    f, d = byid[eid]
    if d.get("march"):
        continue
    items = list(d.items())
    at = next((i for i, (k, _) in enumerate(items) if k == "location"), len(items))
    march = [{"from": a, "to": b, **({"side": s} if s else {}), "note": note}
             for a, b, s, note in legs]
    items.insert(at, ("march", march))
    yaml.safe_dump(dict(items), open(f, "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False)
    n += 1

print(f"补行军路线 {n} 条(共 {len(MARCH)} 个映射,"
      f"{sum(len(v) for v in MARCH.values())} 段)")
