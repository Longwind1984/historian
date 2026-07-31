#!/usr/bin/env python3
"""给 22 位无纪年的种子人物补时间锚点,使其能上人物轴。

Rick 点1:「甚至包括商代这类没有明确编年的历史,可做模糊化表达」。
前端人物轴要 born+died 俱全才渲染,故周公旦、姜尚、妇好、老子、孙武、廉颇、
蔺相如、范蠡这些人一个都不在轴上——先秦的骨架是空的。

分两类,不一刀切:
  A. 有通说生卒(纵有异说) → born/died + ext.disputed + ext.note 记异说
  B. 生卒确不可考       → floruit_start/end(活跃年代)
     给 B 类编生卒即造假:姜尚传世「前1156-前1017」享年139、老子「莫知其所终」,
     都是后世附会。史学的做法是只记其见于史载的活动区间。

幂等:已有锚点(born/died 或 floruit)即跳过。
"""
import yaml, sys, glob, pathlib

# ── A 类:通说生卒(disputed=有异说,note 记其据) ──
BORN_DIED = {
    "p_wu_zixu":   (-559, -484, "卒年确(前484吴王夫差赐属镂);生年约,史无明文"),
    "p_zichan":    (-580, -522, "卒年确(前522,《左传》昭公二十年);生年系推估"),
    "p_fanli":     (-536, -448, "生卒均约数,史无明文;《史记·越王勾践世家》只记其事"),
    "p_mozi":      (-468, -376, "通说约前468-前376;另有前480-前420等说,学界未定"),
    "p_sunbin":    (-382, -316, "生卒均约数;《史记》只记桂陵(前353)、马陵(前341)二役"),
    "p_lianpo":    (-327, -243, "生卒均约数;确年只有长平(前260)、奔魏入楚(前243后)"),
    "p_sunwu":     (-545, -470, "生卒均约数;《史记》确载者仅仕吴阖闾(前514-前496)间事"),
    "p_bisheng":   (990, 1051, "生卒均约数;仅见沈括《梦溪笔谈》记其庆历中(1041-1048)造活字"),
}

# ── B 类:生卒不可考,只记活跃年代 ──
FLORUIT = {
    "p_yiyin":          (-1600, -1580, "商初,助汤灭夏、历佐外丙中壬至太甲。年代属传说期,无可考编年"),
    "p_fuhao":          (-1250, -1192, "武丁之后。年代随武丁在位(断代工程框架前1250-前1192);卜辞不记生卒"),
    "p_zhou_wen_wang":  (-1099, -1050, "商西伯,受命称王至卒。据夏商周断代工程;传世「享年97」系后世附会"),
    "p_jiang_ziya":     (-1046, -1015, "佐武王牧野灭商(前1046)至封齐。传世「前1156-前1017」享年139,显系附会"),
    "p_zhougong":       (-1042, -1035, "武王崩后摄政七年,东征平三监、营洛邑、制礼作乐。生卒无考"),
    "p_bigan":          (-1060, -1046, "帝辛之叔,官少师,强谏被剖心。年代随商末,生卒无考"),
    "p_gong_bo_he":     (-841, -828, "共和行政十四年。其人本身即因这一段而入史,生卒无考"),
    "p_baosi":          (-779, -771, "幽王三年入宫得宠,至前771犬戎破镐京。生卒无考"),
    "p_laozi":          (-535, -480, "约与孔子同时(孔子问礼于老聃约前518)。《史记》已言「莫知其所终」,生卒本不可考"),
    "p_mengchangjun":   (-321, -279, "袭封于薛至卒(前279)。卒年确,生年无考"),
    "p_linxiangru":     (-283, -260, "完璧归赵(前283)、渑池之会(前279)、将相和。生卒无考"),
    "p_yueyi":          (-284, -279, "率五国兵下齐七十余城(前284)至燕惠王疑之奔赵(前279)。生卒无考"),
    "p_tiandan":        (-279, -265, "即墨火牛阵复齐(前279)至相齐。生卒无考"),
    "p_wang_jian":      (-236, -221, "伐赵(前236起)、灭赵(前228)、灭楚(前223)。生卒无考"),
}

byid = {}
for f in glob.glob("data/entities/persons/*.yaml"):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"):
        byid[d["id"]] = f

missing = [i for i in list(BORN_DIED) + list(FLORUIT) if i not in byid]
if missing:
    print("!! id 不存在,拒绝执行:", missing); sys.exit(1)

def anchored(d):
    return any((d.get(k) or {}).get("year") is not None
               for k in ("born", "died", "floruit_start", "floruit_end"))

n_bd = n_fl = 0
for eid, (b, dd, note) in BORN_DIED.items():
    d = yaml.safe_load(open(byid[eid], encoding="utf-8"))
    if anchored(d): continue
    items = list(d.items())
    at = next(i for i, (k, _) in enumerate(items) if k in ("bio", "roles", "importance"))
    items[at:at] = [("born", {"year": b}), ("died", {"year": dd})]
    d = dict(items)
    ext = d.setdefault("ext", {}); ext["disputed"] = True; ext["note"] = note
    yaml.safe_dump(d, open(byid[eid], "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False)
    n_bd += 1

for eid, (s, e, note) in FLORUIT.items():
    d = yaml.safe_load(open(byid[eid], encoding="utf-8"))
    if anchored(d): continue
    items = list(d.items())
    at = next(i for i, (k, _) in enumerate(items) if k in ("bio", "roles", "importance"))
    items[at:at] = [("floruit_start", {"year": s}), ("floruit_end", {"year": e})]
    d = dict(items)
    ext = d.setdefault("ext", {}); ext["disputed"] = True; ext["note"] = note
    yaml.safe_dump(d, open(byid[eid], "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False)
    n_fl += 1

print(f"通说生卒 {n_bd} 人 / 活跃年代 {n_fl} 人  (共 {len(BORN_DIED)+len(FLORUIT)} 个映射)")
