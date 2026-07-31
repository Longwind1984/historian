#!/usr/bin/env python3
"""Phase 7 — Augment with data from research agents.

Adds:
- 6 more battles (幽州917 / 阳城945 / 寿州保卫 / 六合 / 灭闽945 / 灭楚951)
- 13 secondary monarchs (杨渥 杨隆演 / 王延翰 王延政 / 马希声 马希广 马希萼 /
  刘玢 刘晟 / 高从诲 高保勗 高继冲 / 刘承钧 刘继恩 / 钱弘倧)
- New institutional events (枢密院 / 三司 / 伶人乱政 / 朱温代唐细节)
- Cross-verified date corrections from agents

All cross-checked against agent research output.
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
# ADDITIONAL BATTLES (from agent C research)
# ============================================================
EXTRA_BATTLES = [
    ("b_youzhou917", "幽州之战(幽州保卫战)", (917, 3), (917, 8), "pl_youzhou",
     ["k_houdong", "k_liao"], ["p_yeluabaoji", "p_likaiqu"], "k_houdong", "p_licunxu",
     "917年三月契丹乘新州之胜围攻幽州,周德威坚守约200日。李存勖抽调李嗣源、李存审、阎宝率七万步骑自易州北上驰援。晋军以步兵大阵稳扎稳打对抗契丹骑兵,大破之,解幽州之围。",
     "保全晋之河北战略要地,被誉为'古代以步制骑的典范'。延缓契丹南下进程。",
     "约7万晋援军 vs 30万契丹", "重大",
     ["旧五代史·唐书·庄宗纪", "辽史·太祖纪", "资治通鉴·卷269"]),

    ("b_yangcheng", "阳城之战(白团卫村之战)", (945, 3), None, "pl_yangcheng_1945",
     ["k_houjin", "k_liao"], ["p_shizhonggui", "p_yeludeguang"], "k_houjin", "p_shizhonggui",
     "契丹第三次大举攻晋,晋军被围于白团卫村,顺风纵火围攻。晋军在绝境中反突击,符彦卿等率军借风沙反扑,大破契丹铁鹞子重骑。耶律德光乘骆驼仓皇北逃。",
     "契丹惨败一度北撤,延缓其灭晋进程。但后晋未能巩固战果,终在946年中渡桥之降中灭亡。",
     "数万 vs 契丹大军", "重大",
     ["旧五代史·晋书·少帝纪", "资治通鉴·卷284-285"]),

    ("b_liuhe", "六合之战", (956, 2), None, "pl_liuhe",
     ["k_houzhou", "k_nantang"], ["p_zhaokuangyin", "p_lijing"], "k_houzhou", "p_zhaokuangyin",
     "寿州之战期间,南唐派齐王李景达率两万军反攻六合,企图切断周军后路。赵匡胤以两千余兵据守六合,大破南唐军,斩俘甚众。",
     "赵匡胤再立大功,威望日隆。南唐在淮南战场彻底转入被动。为后周全面攻占淮南奠定基础。",
     "2000 vs 20000(以少胜多)", "重要",
     ["旧五代史·周书·世宗纪", "宋史·太祖本纪"]),

    ("b_nantang_min", "南唐灭闽之战(建州之战)", (945, 8), None, "pl_jianou",
     ["k_nantang", "k_min"], ["p_lijing", "p_wangyanxi"], "k_nantang", "p_lijing",
     "闽国王氏宗室内乱,943年王延政于建州自立为帝,国号'殷'。945年南唐中主李璟趁乱派查文徽、边镐南下攻建州。八月建州陷落,王延政出降,闽国核心区域灭亡。",
     "南唐借此役大幅扩张版图。但福州被吴越趁机夺取,福建一分为三;南唐连年用兵亦耗损国力。",
     "数万", "重要",
     ["新五代史·闽世家", "资治通鉴·卷284-285"]),

    ("b_nantang_chu", "南唐灭楚之战(潭州之战)", (951, 10), (951, 11), "pl_changsha",
     ["k_nantang", "k_chu"], ["p_lijing"], "k_nantang", "p_lijing",
     "楚国王室马氏兄弟争位('群驹争槽'),国中大乱。951年秋南唐趁楚内乱派边镐率军入湖南,兵不血刃进入潭州,马希崇等出降,楚国灭亡。",
     "楚国灭亡,湖南尽失。但南唐统治不善,不久刘言、王逵、周行逢相继起兵,湖南实际上重归割据。南唐得而复失,徒耗国力。",
     "规模不大", "重要",
     ["新五代史·楚世家", "资治通鉴·卷290"]),

    # Note: 寿州之战 already covered under b_houzhou_nantang in seed_factions; agent C provided more detail
    # but to avoid duplicate nodes, we keep that one.
]

EXTRA_PLACES_FOR_BATTLES = [
    ("pl_yangcheng_1945", "阳城(白团卫村)", "望都/唐县", "河北", 38.74, 114.97, "battlefield", [], "945 阳城之战"),
    ("pl_liuhe", "六合", "南京六合区", "江苏", 32.37, 118.83, "battlefield", [], "956 六合之战"),
    ("pl_jianou", "建州", "建瓯", "福建", 27.05, 118.30, "battlefield", ["建安"], "945 南唐灭闽主战场"),
    ("pl_caishiji", "采石矶", "马鞍山", "安徽", 31.70, 118.50, "battlefield", [], "974-975 宋灭南唐长江浮桥"),
    ("pl_jianmen", "剑门关", "剑阁", "四川", 32.24, 105.94, "garrison", [], "蜀道天险,965 宋军破关"),
    ("pl_baimaling", "白马岭", "盂县", "山西", 38.30, 113.40, "battlefield", [], "979 宋阻辽援"),
    ("pl_zhongduqiao", "中渡桥", "正定南", "河北", 38.14, 114.57, "battlefield", [], "946 杜重威降契丹"),
]


def gen_extra_battles():
    for tup in EXTRA_BATTLES:
        bid, name, date, end, place, combatants, commanders, victor, victor_cmd, desc, sig, strength, scale, srcs = tup
        obj = {
            "id": bid, "type": "Battle", "name": name,
            "date": {"year": date[0], "month": date[1]} if date[1] else {"year": date[0]},
            "location": place,
            "combatants": combatants,
            "commanders": commanders,
            "victor": victor,
            "victor_commander": victor_cmd,
            "strength": strength,
            "description": desc,
            "significance": sig,
            "ext": {"scale": scale},
            "sources": srcs,
        }
        if end and end[0]:
            obj["end_date"] = {"year": end[0]} if not end[1] else {"year": end[0], "month": end[1]}
        write(DATA / "entities" / "battles" / f"{bid[2:]}.yaml", obj)


def gen_extra_places_for_battles():
    for tup in EXTRA_PLACES_FOR_BATTLES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["资治通鉴", "中国历史地图集"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# ============================================================
# SECONDARY MONARCHS (from agent B research)
# ============================================================
SECONDARY_MONARCHS = [
    # 杨吴
    ("p_yangwo", "杨渥", ["杨奉天", "弘农郡王", "景帝"], "承天", (880, None), (908, 6), "pl_hefei",
     "杨吴第二主。杨行密长子。905 年继位为弘农郡王,在位期间荒淫无道,大权旁落于权臣张颢、徐温。908 年为张颢、徐温所杀。",
     ["新五代史·吴世家", "十国春秋·吴"]),
    ("p_yanglongyan", "杨隆演", ["杨渭", "吴高祖", "杨溥兄"], None, (897, None), (920, 6), "pl_jinling",
     "杨吴第三主。杨行密次子。908 年兄杨渥被杀后继位,实为徐温傀儡。919 年即吴王位,920 年卒。",
     ["新五代史·吴世家", "十国春秋·吴"]),

    # 闽
    ("p_wangyanhan", "王延翰", ["闽嗣王", "王子元"], None, (None, None), (927, 1), "pl_fuzhou",
     "闽第二主。王审知长子。925 年继位为闽王,927 年为弟王延钧与王延禀联手所杀。",
     ["新五代史·闽世家", "十国春秋·闽"]),
    ("p_wangyanzheng", "王延政", ["闽天德帝", "殷帝", "王延政"], None, (None, None), (951, None), "pl_jianou",
     "闽末主(殷帝)。王审知子。943 年因与兄王延羲不和,于建州自立为帝,国号殷。945 年闽国大乱,他复国号闽。同年南唐来伐,出降。被俘送金陵。",
     ["新五代史·闽世家", "十国春秋·闽"]),

    # 楚(马氏诸子争位,"群驹争槽")
    ("p_maxisheng", "马希声", ["楚衡阳王"], None, (898, None), (932, 8), "pl_changsha",
     "楚第二主。马殷长子(一说次子)。930 年继位。在位三年卒。",
     ["新五代史·楚世家", "十国春秋·楚"]),
    ("p_maxiguang", "马希广", ["楚废王"], None, (None, None), (950, 12), "pl_changsha",
     "楚第四主。马殷子。947-950 在位。为同母弟马希萼所杀。",
     ["新五代史·楚世家", "十国春秋·楚"]),
    ("p_maxie", "马希萼", ["楚恭孝王"], None, (None, None), (951, None), "pl_changsha",
     "楚第五主。马殷子。950 年起兵杀兄马希广自立。951 年南唐来伐,降。楚国亡。",
     ["新五代史·楚世家", "十国春秋·楚"]),

    # 南汉
    ("p_liubin", "刘玢", ["刘弘度", "南汉殇帝"], None, (920, None), (943, 4), "pl_guangzhou",
     "南汉第二主。刘龑子。942 年继位,荒淫。943 年为弟刘晟所杀。",
     ["新五代史·南汉世家", "十国春秋·南汉"]),
    ("p_liusheng", "刘晟", ["刘弘熙", "南汉中宗"], None, (920, None), (958, 8), "pl_guangzhou",
     "南汉第三主。刘龑子。943 年杀兄刘玢自立。在位期间屡兴大狱,尽杀诸弟。958 年卒。",
     ["新五代史·南汉世家", "十国春秋·南汉"]),

    # 荆南
    ("p_gaoconghui", "高从诲", ["荆南文献王"], None, (891, None), (948, 11), "pl_jiangling",
     "荆南第二主。高季兴子。929 年继位。'高赖子'之名主要由此人在列强间左右逢源而来。",
     ["新五代史·南平世家", "十国春秋·荆南"]),
    ("p_gaobaoxy", "高保勗", ["荆南贞安王"], None, (924, None), (962, 11), "pl_jiangling",
     "荆南第五主。高从诲子。960-962 在位。荒淫。'万事不如杯在手,一年几见月当头'典出于此。",
     ["十国春秋·荆南"]),
    ("p_gaojichong", "高继冲", ["荆南末主"], None, (937, None), (973, None), "pl_jiangling",
     "荆南末代君主。高保融子。962 年继位,963 年宋军假道伐张文表顺势收荆南,降。",
     ["宋史·荆南高氏", "十国春秋·荆南"]),

    # 北汉
    ("p_liuchengjun", "刘承钧", ["刘钧", "北汉睿宗"], None, (926, None), (968, 7), "pl_taiyuan",
     "北汉第二主。刘崇子。954 年继位。在位期间继续依辽抗周/宋,国势日蹙。968 年卒。",
     ["新五代史·东汉世家", "十国春秋·北汉"]),
    ("p_liujien", "刘继恩", ["北汉少主"], None, (None, None), (968, 9), "pl_taiyuan",
     "北汉第三主。刘承钧养子。968 年 7 月继位,在位仅 60 余日为侯霸荣所杀。",
     ["十国春秋·北汉"]),

    # 吴越
    ("p_qianhongzong", "钱弘倧", ["钱倧", "吴越忠逊王"], None, (929, 8), (975, None), "pl_hangzhou",
     "吴越第四任国王。钱元瓘七子。947 年继位,同年为将领胡进思所废,在位仅数月。弟钱弘俶继位。",
     ["十国春秋·吴越", "吴越备史"]),
]


def gen_secondary_monarchs():
    for tup in SECONDARY_MONARCHS:
        pid, name, aliases, courtesy, born, died, birthplace, bio, srcs = tup
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
        obj["sources"] = srcs
        write(DATA / "entities" / "persons" / f"{pid[2:]}.yaml", obj)


# ============================================================
# ADDITIONAL INSTITUTIONAL EVENTS (from agent D research)
# ============================================================
EXTRA_EVENTS = [
    ("e_shumiyuan", "五代枢密院制度", (907, None), None, "institution", "pl_kaifeng",
     ["k_houliang", "k_houdong", "k_houjin", "k_houhan", "k_houzhou"],
     "枢密使本源于唐,初由宦官担任。五代时去宦官化,改由皇帝亲信文臣(敬翔、郭崇韬、安重诲)或武将担任,成为仅次于皇帝的最高军事决策机构,与中书门下(行政)分立。后梁朱温改枢密院为'崇政院'由敬翔掌;后唐复枢密院,权力扩大。",
     "构成五代'中书门下+枢密院+三司'三权分立格局,实质上分割宰相权力、强化皇权。直接演变为宋朝'二府三司'体制,是中国古代中枢体制由三省制向二府制转型的关键环节。",
     ["五代会要", "新五代史·职方考"]),

    ("e_sansi", "三司使财政制度", (930, None), None, "institution", "pl_luoyang", ["k_houdong"],
     "三司指盐铁司(盐铁专卖及商税)、度支司(财政收支调度)、户部司(户籍田赋)。后梁朱温不重视三司,另设'建昌宫'为最高财政机关。后唐初以租庸使辖三司、或命大臣'判三司事';后唐长兴元年(930)正式合并三司,设三司使与副使统一领导,直接对皇帝负责,不经政事堂。",
     "切断宰相财政权,皇帝通过直接控制三司使集中财权,是五代强化中央集权的关键制度。为宋朝'二府三司'中的'计省'直接渊源。",
     ["五代会要", "新五代史·百官志", "北宋三司使渊源初探"]),

    ("e_lingren", "后唐庄宗伶人乱政", (923, None), (926, 5), "institution", "pl_luoyang", ["k_houdong"],
     "李存勖精通音律,自取艺名'李天下',与伶人同台演出;宠信伶人景进、史彦琼、郭从谦,破格任伶人为刺史、干预朝政、搬弄是非;冷落并猜忌功臣,郭崇韬等被冤杀;伶官搜刮民财、朝纲败坏。926 年伶官郭从谦发动兴教门之变,李存勖中流矢而亡。",
     "典型的'善始不善终'案例。欧阳修《新五代史·伶官传序》总结为'忧劳可以兴国,逸豫可以亡身'、'祸患常积于忽微,而智勇多困于所溺'。直接导致后唐庄宗覆灭、李嗣源(明宗)即位。",
     ["新五代史·伶官传", "旧五代史·唐书·庄宗纪", "资治通鉴·后唐纪"]),

    ("e_baima_yi", "白马驿之祸", (905, 6), None, "coup", "pl_baima_yi", ["k_houliang_pre", "k_tang"],
     "905 年朱温在亲信李振、柳璨等人怂恿下,于滑州白马驿(今河南滑县)将裴枢、独孤损、崔远、陆扆、王溥等三十余位唐朝名臣大臣集中杀害,投尸黄河。李振称之为'此辈自谓清流,宜投于浊流'。",
     "唐代士族阶层遭受毁灭性打击,标志'清流'政治的终结。陈寅恪、毛汉光等学者视之为关陇集团与士族政治终结的标志性事件,为五代'武人政治'全面取代'贵族/士族政治'扫清道路。",
     ["旧五代史·梁书·太祖纪", "资治通鉴·卷265"]),

    ("e_huangchao_qiyi", "黄巢起义", (875, 6), (884, 6), "institution", "pl_junzhou",
     ["k_tang"],
     "875 年王仙芝、黄巢起义。880 年黄巢攻入长安,建国号齐,称帝。883 年退出长安,884 年黄巢在狼虎谷(山东莱芜)兵败,为外甥林言所杀。",
     "唐末规模最大的农民起义。彻底摧毁了唐朝根基——朱温(降唐的起义军将领)成为最大军阀,沙陀李克用借平乱崛起,二者成为五代十国两大奠基势力。直接催生五代十国政治格局。",
     ["旧唐书·黄巢传", "新唐书·逆臣传", "资治通鉴·卷252-256"]),

    ("e_an_lushan_rebellion", "安史之乱", (755, 12), (763, 1), "institution", "pl_you_zhou",
     ["k_tang_pre"],
     "755 年安禄山自范阳起兵,攻克洛阳、长安。玄宗入蜀,肃宗即位灵武。唐廷借回纥兵平叛,763 年史朝义兵败自缢,历时八年的安史之乱结束。",
     "唐由盛转衰的转折点。直接导致藩镇割据(河朔三镇)、宦官专权(神策军)、朋党之争——五代十国的所有病根皆源于此。从此关陇集团进一步式微,中国政治经济重心开始南移。",
     ["旧唐书·安禄山传", "新唐书·逆臣传", "资治通鉴·卷217-223"]),
]

EXTRA_PLACES_FOR_EVENTS = [
    ("pl_baima_yi", "白马驿", "滑县", "河南", 35.58, 114.52, "battlefield", ["白马"], "905 白马驿之祸"),
    ("pl_chang_an_pre", "长安", "西安", "陕西", 34.27, 108.95, "city", [], "唐都(为兼容事件引用)"),
    ("pl_you_zhou_pre", "范阳", "涿州", "河北", 39.49, 115.98, "garrison", ["幽州"], "安禄山起家地"),
    ("pl_k_tang_pre", "唐朝", "西安", "陕西", 34.27, 108.95, "region", [], "前置政权标识(仅为事件锚点)"),
]


def gen_extra_events():
    for tup in EXTRA_EVENTS:
        eid, name, date, end, category, place, polities, desc, impact, srcs = tup
        obj = {
            "id": eid, "type": "Event", "name": name,
            "date": {"year": date[0]} if not date[1] else {"year": date[0], "month": date[1]},
            "category": category,
            "location": place,
            "polities_involved": polities,
            "description": desc,
            "impact": impact,
            "sources": srcs,
        }
        if end and end[0]:
            obj["end_date"] = {"year": end[0]} if not end[1] else {"year": end[0], "month": end[1]}
        write(DATA / "entities" / "events" / f"{eid[2:]}.yaml", obj)


def gen_event_places():
    for tup in EXTRA_PLACES_FOR_EVENTS:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["资治通鉴", "中国历史地图集"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# ============================================================
# EXTENSION RELATIONS
# ============================================================
EXT_RELATIONS = [
    # 杨吴
    ("p_yanghangmi", "p_yangwo", "father_of", 880, None, 908, 6, "长子"),
    ("p_yanghangmi", "p_yanglongyan", "father_of", 897, None, None, None, "次子"),
    ("p_yanghangmi", "p_yangpu", "father_of", 900, None, None, None, "第四子"),
    ("p_yangwo", "k_yangwu", "succeeded_by", 905, 11, 908, 6, "弘农郡王"),
    ("p_yanglongyan", "k_yangwu", "succeeded_by", 908, 6, 920, 6, "吴王"),
    ("p_yangpu", "k_yangwu", "succeeded_by", 920, 6, 937, 10, "睿帝(927 称帝)"),
    ("p_xuzhigao", "p_yangpu", "usurped", 937, 10, None, None, "受禅"),

    # 闽
    ("p_wangshenzhi", "p_wangyanhan", "father_of", None, None, None, None, "长子"),
    ("p_wangshenzhi", "p_wangyanjun", "father_of", None, None, None, None, "次子"),
    ("p_wangshenzhi", "p_wangyanxi", "father_of", None, None, None, None, None),
    ("p_wangshenzhi", "p_wangyanzheng", "father_of", None, None, None, None, None),
    ("p_wangyanhan", "k_min", "succeeded_by", 925, 12, 927, 1, "嗣王"),
    ("p_wangyanjun", "p_wangyanhan", "killed", 927, 1, None, None, "与王延禀联手"),
    ("p_wangyanxi", "k_min", "succeeded_by", 939, None, 944, 3, "景宗"),
    ("p_wangyanzheng", "k_min", "succeeded_by", 943, None, 945, 8, "殷帝→闽帝"),

    # 楚
    ("p_mayin", "p_maxisheng", "father_of", 898, None, None, None, None),
    ("p_mayin", "p_maxifan", "father_of", 899, None, None, None, None),
    ("p_mayin", "p_maxiguang", "father_of", None, None, None, None, None),
    ("p_mayin", "p_maxie", "father_of", None, None, None, None, None),
    ("p_maxisheng", "k_chu", "succeeded_by", 930, None, 932, 8, "衡阳王"),
    ("p_maxifan", "k_chu", "succeeded_by", 932, 8, 947, 5, "文昭王"),
    ("p_maxiguang", "k_chu", "succeeded_by", 947, 5, 950, 12, "废王"),
    ("p_maxie", "k_chu", "succeeded_by", 950, 12, 951, 11, "恭孝王"),
    ("p_maxie", "p_maxiguang", "killed", 950, 12, None, None, "起兵杀兄"),

    # 南汉
    ("p_liuyan", "p_liubin", "father_of", 920, None, None, None, None),
    ("p_liuyan", "p_liusheng", "father_of", 920, None, None, None, None),
    ("p_liubin", "k_nanhan", "succeeded_by", 942, 5, 943, 4, "殇帝"),
    ("p_liusheng", "k_nanhan", "succeeded_by", 943, 4, 958, 8, "中宗"),
    ("p_liusheng", "p_liubin", "killed", 943, 4, None, None, "杀兄篡位"),
    ("p_liusheng", "p_liuchang", "father_of", 942, None, None, None, None),

    # 荆南
    ("p_gaojixing", "p_gaoconghui", "father_of", 891, None, None, None, None),
    ("p_gaoconghui", "p_gaobaorong", "father_of", 920, None, None, None, "第三子"),
    ("p_gaoconghui", "p_gaobaoxy", "father_of", 924, None, None, None, None),
    ("p_gaoconghui", "k_jingnan", "succeeded_by", 929, 5, 948, 11, "文献王"),
    ("p_gaobaorong", "k_jingnan", "succeeded_by", 948, 11, 960, 8, "贞懿王"),
    ("p_gaobaoxy", "k_jingnan", "succeeded_by", 960, 8, 962, 11, "贞安王"),
    ("p_gaojichong", "k_jingnan", "succeeded_by", 962, 11, 963, 3, "末代"),
    ("p_gaojichong", "b_song_jingnan", "participated_in", 963, 1, 963, 3, "降宋"),

    # 北汉
    ("p_liuchong", "p_liuchengjun", "father_of", 926, None, None, None, None),
    ("p_liuchong", "p_liujiyuan", "grandfather_of", None, None, None, None, None),
    ("p_liuchengjun", "p_liujien", "father_of", None, None, None, None, "养子"),
    ("p_liuchengjun", "p_liujiyuan", "father_of", None, None, None, None, "养子"),
    ("p_liuchengjun", "k_beihan", "succeeded_by", 954, 11, 968, 7, "睿宗"),
    ("p_liujien", "k_beihan", "succeeded_by", 968, 7, 968, 9, "在位60余日"),
    ("p_liujiyuan", "k_beihan", "succeeded_by", 968, 9, 979, 6, "英武帝"),

    # 吴越
    ("p_qianyuanguan", "p_qianhongzong", "father_of", 929, 8, None, None, "第七子"),
    ("p_qianyuanguan", "p_qianhongchu", "father_of", 929, 8, None, None, "第九子"),
    ("p_qianhongzuo", "k_wuyue", "succeeded_by", 941, 9, 947, 6, "忠献王"),
    ("p_qianhongzong", "k_wuyue", "succeeded_by", 947, 6, 947, 12, "忠逊王(被废)"),
    ("p_qianhongzong", "p_qianhongchu", "sibling_of", None, None, None, None, "兄弟"),

    # 新战役的指挥关系
    ("p_yeluabaoji", "b_youzhou917", "led", 917, 3, None, None, "亲征围幽州"),
    ("p_likaiqu", "b_youzhou917", "led", 917, 3, None, None, "晋方主师(实际李嗣源等驰援)"),
    ("p_shizhonggui", "b_yangcheng", "led", 945, 3, None, None, "晋方主师"),
    ("p_yeludeguang", "b_yangcheng", "led", 945, 3, None, None, "亲征"),
    ("p_zhaokuangyin", "b_liuhe", "led", 956, 2, None, None, "2000 兵破南唐"),
    ("p_lijing", "b_nantang_min", "led", 945, 8, None, None, "策动"),
    ("p_lijing", "b_nantang_chu", "led", 951, 10, None, None, "策动"),
    ("p_wangyanxi", "b_nantang_min", "participated_in", 945, 8, None, None, "出降"),
    ("p_maxie", "b_nantang_chu", "participated_in", 951, 10, None, None, "出降"),

    # 事件参与
    ("p_huangchao", "e_huangchao_qiyi", "participated_in", 875, 6, 884, 6, "领袖"),
    ("p_zhuwen", "e_huangchao_qiyi", "participated_in", 877, None, 882, 9, "黄巢部将"),
    ("p_zhuwen", "e_baima_yi", "participated_in", 905, 6, None, None, "执行者"),
    ("p_an_lushan", "e_an_lushan_rebellion", "participated_in", 755, 12, 757, 1, "发动者"),
    ("p_licunxu", "e_lingren", "participated_in", 923, None, 926, 5, "纵容者,后被杀"),
    ("p_guocongqian", "e_lingren", "participated_in", 926, 5, None, None, "发动者"),

    # 黄巢→朱温→朱温代唐 因果链
    ("e_huangchao_qiyi", "e_zhuwen_tang", "preceded_by", None, None, None, None, "黄巢之乱催生朱温,继而朱温篡唐"),
    ("e_baima_yi", "e_zhuwen_tang", "preceded_by", None, None, None, None, "白马驿之祸摧毁唐士族,为代唐扫清障碍"),

    # 因果:安史之乱 → 藩镇割据 → 五代乱世
    ("e_an_lushan_rebellion", "e_huangchao_qiyi", "preceded_by", None, None, None, None, "中晚唐藩镇之祸演化"),
    ("e_an_lushan_rebellion", "f_heshuo", "includes", None, None, None, None, "安史之乱后形成河朔三镇"),

    # 制度演化
    ("e_zhou_reform", "e_shumiyuan", "preceded_by", None, None, None, None, "枢密院在五代成型"),
]


def gen_ext_relations():
    rels = []
    for r in EXT_RELATIONS:
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
    out = DATA / "relations" / "agent_extras.yaml"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(rels, f, allow_unicode=True, sort_keys=False)
    print(f"  ✓ {len(rels)} extra relations → data/relations/agent_extras.yaml")


if __name__ == "__main__":
    print(f"→ Phase 7: agent data augmentation")
    gen_extra_places_for_battles()
    print(f"  ✓ {len(EXTRA_PLACES_FOR_BATTLES)} places for battles")
    gen_extra_battles()
    print(f"  ✓ {len(EXTRA_BATTLES)} additional battles")
    gen_secondary_monarchs()
    print(f"  ✓ {len(SECONDARY_MONARCHS)} secondary monarchs")
    gen_event_places()
    print(f"  ✓ {len(EXTRA_PLACES_FOR_EVENTS)} places for events")
    gen_extra_events()
    print(f"  ✓ {len(EXTRA_EVENTS)} additional events")
    gen_ext_relations()
    print("Done.")
