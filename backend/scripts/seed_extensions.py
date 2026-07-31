#!/usr/bin/env python3
"""Phase 6 — Extension data: Tang / Song / Liao / Jin / Yuan / Ming / Qing stubs.

Proves the open schema handles pre-5D and post-5D eras, including cross-era
factions (关陇集团 spans N.Wei→Sui→Tang) and the Dynasty node type added here.

This file adds:
- New Dynasty node type (registered via schema/dynasty.yaml)
- 7 Dynasty entities (Tang / Song / Liao / Jin / Yuan / Ming / Qing)
- Late-Tang figures (Huang Chao, An Lushan — context for 5D)
- Song/Southern-Song figures (Zhao Guangyi, Yue Fei, Wang Anshi)
- Cross-era relations

All carry sources. Dates follow《中国历代帝王世系年表》.
"""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)


# ============================================================
# DYNASTIES — 7 大朝代节点 (用于跨朝代索引)
# ============================================================
DYNASTIES = [
    ("d_sui", "隋", "Sui", (581, 3), (618, 5), "p_yangjian", "pl_chang_an",
     "隋朝。581 年杨坚代周建隋,589 年灭陈统一。开皇之治。604 炀帝继位,大兴土木,致乱。618 亡。",
     "隋", ["隋书", "北史·隋本纪"]),
    ("d_tang", "唐", "Tang", (618, 5), (907, 4), "p_liyuan", "pl_chang_an",
     "唐朝。618 年李渊代隋。盛唐(626-755)、中晚唐(755-907)。中国历史上影响最深远的朝代之一。907 年朱温篡唐,五代开始。",
     "隋唐", ["旧唐书", "新唐书", "资治通鉴·唐纪"]),
    ("d_song", "宋", "Song", (960, 2), (1279, 2), "p_zhaokuangyin", "pl_kaifeng",
     "宋朝。960 年赵匡胤陈桥兵变代后周。北宋(960-1127)都开封,南宋(1127-1279)都临安。文化经济高峰,军事弱势。1279 年崖山海战亡于元。",
     "宋", ["宋史", "续资治通鉴长编"]),
    ("d_liao", "辽", "Liao", (916, 1), (1125, 8), "p_yeluabaoji", "pl_liaoshangjing",
     "契丹/辽朝。916 年耶律阿保机称帝。947 年改国号辽。占有燕云十六州。1125 年亡于金。",
     "辽宋夏金", ["辽史", "契丹国志"]),
    ("d_jin_jurchen", "金", "Jin", (1115, 1), (1234, 2), None, "pl_jin_zhongdu",
     "女真金朝。1115 年完颜阿骨打建国,1234 亡于蒙古宋联军。灭辽(1125)、北宋(1127)。",
     "辽宋夏金", ["金史"]),
    ("d_yuan", "元", "Yuan", (1271, 11), (1368, 8), None, "pl_dadu",
     "元朝。1206 年成吉思汗建蒙古国,1271 年忽必烈定国号元,1279 灭南宋统一。1368 明军克大都,元廷北遁(北元)。",
     "元", ["元史", "新元史"]),
    ("d_ming", "明", "Ming", (1368, 1), (1644, 3), "p_zhuyuanzhang", "pl_nanjing_ming",
     "明朝。1368 年朱元璋建,初都南京,永乐迁北京。1644 年李自成入京,崇祯自缢。南明延续至 1662。",
     "明", ["明史"]),
    ("d_qing", "清", "Qing", (1636, None), (1912, 2), None, "pl_beijing",
     "清朝。1616 努尔哈赤建后金,1636 改国号清。1644 入关。1912 逊位,中国帝制结束。",
     "清", ["清史稿"]),
]


def gen_dynasties():
    for tup in DYNASTIES:
        did, name, en, founded, ended, founder, capital, desc, period, srcs = tup
        obj = {
            "id": did, "type": "Dynasty", "name": name,
            "name_en": en,
            "founded": {"year": founded[0], "month": founded[1]} if founded[1] else {"year": founded[0]},
            "ended": {"year": ended[0], "month": ended[1]} if ended[1] else {"year": ended[0]},
            "last_capital": capital,
            "description": desc,
            "period_label": period,
            "sources": srcs,
        }
        if founder:
            obj["founder"] = founder
        write(DATA / "entities" / "dynasties" / f"{did[2:]}.yaml", obj)


# ============================================================
# EXTRA PLACES (for dynasties + new persons)
# ============================================================
EXTRA_PLACES = [
    ("pl_jin_zhongdu", "中都", "北京", "北京", 39.91, 116.40, "capital", ["大兴"], "金中都"),
    ("pl_dadu", "大都", "北京", "北京", 39.91, 116.40, "capital", ["汗八里"], "元大都"),
    ("pl_nanjing_ming", "应天府", "南京", "江苏", 32.04, 118.78, "capital", ["金陵", "南京"], "明初都城"),
    ("pl_beijing", "北京", "北京", "北京", 39.91, 116.40, "capital", ["顺天", "北平"], "明清都城"),
    ("pl_caizhou", "蔡州", "汝南", "河南", 33.00, 114.36, "battlefield", [], "金哀宗自缢处"),
    ("pl_linan", "临安", "杭州", "浙江", 30.27, 120.16, "capital", ["杭州"], "南宋都城(原吴越地)"),
    ("pl_yashan", "崖山", "新会", "广东", 22.51, 113.04, "battlefield", [], "1279 崖山海战"),
    ("pl_junzhou", "曹州", "菏泽", "山东", 35.24, 115.47, "birthplace", [], "黄巢籍贯"),
    ("pl_yingzhou_late_tang", "颍州", "阜阳", "安徽", 32.89, 115.82, "birthplace", [], "晚唐相关"),
    ("pl_you_zhou", "范阳", "涿州", "河北", 39.49, 115.98, "garrison", ["幽州"], "安禄山起家地"),
    ("pl_fenyang", "汾阳", "汾阳", "山西", 37.27, 111.78, "birthplace", ["汾州"], "郭子仪封地"),
    ("pl_xiangzhou", "相州", "安阳", "河南", 36.10, 114.39, "battlefield", [], "安史之乱战场"),
    ("pl_taiyuan_song", "太原", "太原", "山西", 37.77, 112.55, "city", ["并州"], "北宋重镇"),
    ("pl_zhongdu_zhu", "涿州", "涿州", "河北", 39.49, 115.98, "birthplace", [], "赵匡胤祖籍/朱元璋先世"),
    ("pl_huaiyin", "淮阴", "淮安", "江苏", 33.51, 119.02, "birthplace", [], "韩信故里(参考)"),
    ("pl_qingzhou_song", "青州", "青州", "山东", 36.68, 118.48, "city", [], "京东东路"),
    ("pl_linzhi_song", "临淄", "淄博", "山东", 36.81, 118.31, "city", [], "宋金战场"),
]


def gen_extra_places():
    for tup in EXTRA_PLACES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
        }
        if aliases:
            obj["aliases"] = aliases
        obj["sources"] = ["中国历史地图集", "旧唐书·地理志", "宋史·地理志"]
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# ============================================================
# LATE-TANG figures (晚唐,五代十国的前夜)
# ============================================================
LATE_TANG_PERSONS = [
    ("p_huangchao", "黄巢", ["黄天霸", "冲天大将军"], None, (820, None), (884, 6), "pl_junzhou",
     "唐末农民起义领袖。875 年起兵,880 年攻入长安称帝,国号齐。884 年战败,在狼虎谷为外甥林言所杀。其部将朱温后降唐,成为后梁太祖。",
     "唐末大起义摧毁了唐朝根基,直接催生五代十国格局。",
     ["旧唐书·黄巢传", "新唐书·逆臣传", "资治通鉴·卷252-256"]),
    ("p_an_lushan", "安禄山", ["安轧荦山"], None, (703, None), (757, 1), "pl_you_zhou",
     "唐代胡人将领。营州柳城人(粟特+突厥血统)。受玄宗宠信,身兼三镇节度使。755 年发动安史之乱,756 年称帝,国号燕。757 年为子安庆绪所杀。",
     "安史之乱(755-763)是唐由盛转衰的转折,直接导致藩镇割据、河朔三镇、宦官专权——五代十国的所有病根皆源于此。",
     ["旧唐书·安禄山传", "新唐书·逆臣传", "资治通鉴·卷217-220"]),
    ("p_shi_siming", "史思明", ["史窣干"], None, (703, None), (761, 4), "pl_you_zhou",
     "安史之乱主要首领之一。突厥血统,安禄山旧友。安庆绪杀安禄山后,史思明继领叛军。759 年称帝。761 年为子史朝义所杀。",
     "与安禄山并称'安史',深度塑造中晚唐格局。",
     ["旧唐书·史思明传", "资治通鉴·卷221-222"]),
    ("p_guo_ziyi", "郭子仪", ["郭令公", "汾阳王"], None, (697, None), (781, 6), "pl_fenyang",
     "中唐名将。安史之乱主力平叛者,封汾阳郡王。历仕四朝,寿至85岁,功盖天下而主不疑。",
     "中唐柱石。其部属后衍生河朔藩镇问题,影响五代政治。",
     ["旧唐书·郭子仪传", "新唐书·郭子仪传"]),

    # 宋初/北宋重要人物
    ("p_zhaoguangyi", "赵光义", ["赵炅", "宋太宗"], "廷宜", (939, None), (997, 3), "pl_kaifeng",
     "宋太宗。赵匡胤亲弟。976 年继位(烛影斧声疑案)。979 年灭北汉,完成局部统一。两度伐辽皆败(高梁河之战、雍熙北伐)。大兴文治,扩大科举。",
     "完成宋统一(本部),确立崇文抑武国策。",
     ["宋史·太宗本纪", "续资治通鉴长编·卷17-41"]),
    ("p_yuefei", "岳飞", ["岳鹏举"], "鹏举", (1103, None), (1142, 1), "pl_anyang",
     "南宋抗金名将。出身行伍。一生抗金,1140 年郾城大捷。为高宗、秦桧以'莫须有'罪名杀害。",
     "中国历史上的忠勇象征。1141 年绍兴和议奠定南北对峙。",
     ["宋史·岳飞传", "鄂国金佗稡编"]),
    ("p_wanganshi", "王安石", ["王介甫", "王半山"], "介甫", (1021, 12), (1086, 5), "pl_linchuan",
     "北宋政治家、文学家、思想家。神宗熙宁年间(1069-1076)推行变法(青苗/募役/市易/保甲等)。因保守派反对和新法执行扭曲而失败。",
     "北宋最大政治事件,影响南宋以降党争和经世思想。",
     ["宋史·王安石传", "临川先生文集"]),
    ("p_sima_guang", "司马光", ["司马君实"], "君实", (1019, None), (1086, 9), "pl_xiaxian",
     "北宋政治家、史学家。保守派领袖,反对王安石变法。主编《资治通鉴》。1085 高太后临朝,起为相,废新法。",
     "《资治通鉴》是中国史学的不朽巨著。",
     ["宋史·司马光传", "资治通鉴"]),

    # 关陇集团额外成员(跨朝代)
    ("p_duguxin", "独孤信", ["独孤如愿"], "期弥头", (503, None), (557, 4), "pl_yuncheng_gu",
     "西魏八大柱国之一。三女皆为皇后(北周明敬后、隋文献后、唐元贞后),中国历史独一无二。关陇集团核心。",
     "关陇集团联姻政治的极致体现。",
     ["周书·独孤信传", "陈寅恪·唐代政治史述论稿"]),
    ("p_lihu", "李虎", ["李文彬"], None, (None, None), (551, None), "pl_chengji",
     "西魏八大柱国之一,唐太祖李渊祖父。李唐皇室的源头。",
     "李唐皇室祖先,关陇集团核心。",
     ["旧唐书·高祖本纪"]),
    ("p_liyuan", "李渊", ["唐高祖"], "叔德", (566, 4), (635, 6), "pl_chengji",
     "唐朝建立者。李虎孙,北周贵族。617 年太原起兵,618 年代隋建唐。在位期间基本统一。626 年玄武门之变后,被世民所迫退位。",
     "大唐奠基。",
     ["旧唐书·高祖本纪", "新唐书·高祖本纪", "资治通鉴·卷184-191"]),

    # 元明清开国之君(几个示范)
    ("p_zhuyuanzhang", "朱元璋", ["明太祖", "朱洪武", "朱兴宗", "朱重八"], "国瑞", (1328, 10), (1398, 6), "pl_fengyang",
     "明朝建立者。出身赤贫,早年为僧乞讨。1352 年投郭子兴红巾军,逐步兼并群雄。1368 年称帝建明,定都南京。北伐灭元,统一中国。",
     "中国历史上唯一从赤贫到统一的开国皇帝。",
     ["明史·太祖本纪"]),
    ("p_hubilai", "忽必烈", ["元世祖", "薛禅汗"], None, (1215, 9), (1294, 2), "pl_dadu",
     "元朝建立者。成吉思汗孙,蒙哥弟。1260 年称大汗,1271 年定国号元。1279 年崖山海战灭南宋,统一中国。",
     "完成中国全境统一,定都大都,奠元明格局。",
     ["元史·世祖本纪", "新元史"]),
]


def gen_late_tang():
    for tup in LATE_TANG_PERSONS:
        pid, name, aliases, courtesy, born, died, birthplace, bio, sig, srcs = tup
        obj = {"id": pid, "type": "Person", "name": name}
        if aliases:
            obj["alias"] = [a for a in aliases if a]
        if courtesy:
            obj["courtesy_name"] = courtesy
        if born and born[0] is not None:
            d = {"year": born[0]}
            if born[1] is not None:
                d["month"] = born[1]
            obj["born"] = d
        if died and died[0] is not None:
            d = {"year": died[0]}
            if died[1] is not None:
                d["month"] = died[1]
            obj["died"] = d
        obj["gender"] = "male"
        if birthplace:
            obj["birthplace"] = birthplace
        obj["bio"] = bio
        if sig:
            obj["ext"] = {"significance": sig}
        obj["sources"] = srcs
        write(DATA / "entities" / "persons" / f"{pid[2:]}.yaml", obj)


# Extra birthplaces for the above
EXT_PLACES_2 = [
    ("pl_anyang", "相州", "安阳", "河南", 36.10, 114.39, "birthplace", [], "岳飞籍贯"),
    ("pl_linchuan", "临川", "抚州", "江西", 27.95, 116.36, "birthplace", [], "王安石籍贯"),
    ("pl_xiaxian", "夏县", "夏县", "山西", 35.14, 111.22, "birthplace", [], "司马光籍贯"),
    ("pl_yuncheng_gu", "云中", "大同", "山西", 40.08, 113.30, "birthplace", [], "独孤信籍贯"),
    ("pl_chengji", "成纪", "天水", "甘肃", 34.58, 105.72, "birthplace", [], "李唐祖籍"),
    ("pl_fengyang", "濠州", "凤阳", "安徽", 32.86, 117.56, "birthplace", ["钟离"], "朱元璋籍贯"),
]


def gen_ext_places_2():
    for tup in EXT_PLACES_2:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
        }
        if aliases:
            obj["aliases"] = aliases
        obj["sources"] = ["中国历史地图集", "旧唐书·地理志"]
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# ============================================================
# EXTENSION RELATIONS
# ============================================================
EXT_RELATIONS = [
    # Dynasty chains
    ("d_sui", "d_tang", "succeeded_by", 618, 5, None, None, None),
    ("d_tang", "d_song", "succeeded_by", 960, 2, None, None, "中间隔五代十国"),
    ("d_song", "d_yuan", "succeeded_by", 1279, 2, None, None, "崖山海战"),
    ("d_liao", "d_jin_jurchen", "succeeded_by", 1125, 8, None, None, "金灭辽"),
    ("d_jin_jurchen", "d_yuan", "succeeded_by", 1234, 2, None, None, "蒙古灭金"),
    ("d_yuan", "d_ming", "succeeded_by", 1368, 1, None, None, "明军克大都"),
    ("d_ming", "d_qing", "succeeded_by", 1644, 3, None, None, "清兵入关"),

    # Dynasty ↔ Polity (includes)
    ("d_tang", "k_tang", "includes", 618, 5, 907, 4, None),
    ("d_song", "k_song", "includes", 960, 2, 1279, 2, None),
    ("d_liao", "k_liao", "includes", 916, 1, 1125, 8, None),
    ("d_song", "k_houzhou", "preceded_by", 960, 2, None, None, "代后周"),

    # Late Tang → 5D causal chain
    ("p_an_lushan", "e_an_lushan_rebellion", "participated_in", 755, 12, 757, 1, "安史之乱发动者") if False else None,
    ("p_an_lushan", "f_heshuo", "leader_of", 742, None, 757, 1, "三镇节度使"),
    ("p_huangchao", "p_zhuwen", "mentored_by", 877, None, 882, 9, "朱温原为黄巢部将"),
    ("p_zhuwen", "p_huangchao", "served_under", 877, None, 882, 9, "黄巢部将"),
    ("p_huangchao", "f_zhuwen_group", "predecessor_of", None, None, None, None, "朱温集团源自黄巢残部"),

    # Guanlong faction
    ("p_yuwentai", "f_guanlong", "founded", 530, None, None, None, "创立者"),
    ("p_duguxin", "f_guanlong", "member_of", 530, None, 557, 4, "八柱国之一"),
    ("p_lihu", "f_guanlong", "member_of", 530, None, 551, None, "八柱国之一"),
    ("p_yangjian", "f_guanlong", "member_of", 541, 7, 604, 8, None),
    ("p_liyuan", "f_guanlong", "member_of", 566, 4, 635, 6, "关陇集团后裔"),
    ("p_duguxin", "p_yangjian", "father_of", None, None, None, None, "杨坚岳父(独孤伽罗之父)"),
    ("p_lihu", "p_liyuan", "grandfather_of", None, None, None, None, None),

    # Founders
    ("p_liyuan", "d_tang", "founded", 618, 5, None, None, "代隋建唐"),
    ("p_liyuan", "k_tang", "founded", 618, 5, None, None, None),
    ("p_zhaoguangyi", "k_song", "succeeded_by", 976, 11, 997, 3, "宋太宗"),
    ("p_zhaokuangyin", "p_zhaoguangyi", "sibling_of", None, None, None, None, "兄弟"),
    ("p_zhaoguangyi", "b_song_beihan", "led", 979, 2, None, None, "亲征"),
    ("p_hubilai", "d_yuan", "founded", 1271, 11, None, None, "定国号元"),
    ("p_zhuyuanzhang", "d_ming", "founded", 1368, 1, None, None, None),
    ("p_zhuyuanzhang", "pl_nanjing_ming", "capital_at", 1368, 1, 1420, None, "初都应天"),

    # Song figures
    ("p_wanganshi", "p_sima_guang", "rival_of", 1069, None, 1086, 5, "变法 vs 反变法"),
    ("p_yuefei", "p_zhaoguangyi", "served_under", None, None, None, None, "北宋末将(实际事徽钦高宗三代)"),
]


def gen_ext_relations():
    rels = []
    for r in EXT_RELATIONS:
        if r is None:
            continue
        f, t, type_, sy, sm, uy, um, note = r
        obj = {"from": f, "to": t, "type": type_}
        if sy is not None:
            d = {"year": sy}
            if sm is not None:
                d["month"] = sm
            obj["since"] = d
        if uy is not None:
            d = {"year": uy}
            if um is not None:
                d["month"] = um
            obj["until"] = d
        if note:
            obj["note"] = note
        rels.append(obj)
    out = DATA / "relations" / "extensions.yaml"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(rels, f, allow_unicode=True, sort_keys=False)
    print(f"  ✓ {len(rels)} extension relations → data/relations/extensions.yaml")


if __name__ == "__main__":
    print(f"→ Phase 6: extension data")
    gen_dynasties()
    print(f"  ✓ {len(DYNASTIES)} dynasties (new node type)")
    gen_extra_places()
    print(f"  ✓ {len(EXTRA_PLACES)} places (capitals + birthplaces)")
    gen_ext_places_2()
    print(f"  ✓ {len(EXT_PLACES_2)} extra birthplaces")
    gen_late_tang()
    print(f"  ✓ {len(LATE_TANG_PERSONS)} cross-era persons (晚唐/宋/元明清)")
    gen_ext_relations()
    print("Done.")
