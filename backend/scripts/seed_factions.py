#!/usr/bin/env python3
"""Generate Faction, Battle, and Event entities for 5D10K."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)


# ============================================================
# FACTIONS — 派系
# ============================================================
FACTIONS = [
    ("f_shatuo", "沙陀军事集团", "military_clan", (860, None), (960, None), "pl_hedong",
     "突厥沙陀部族(处月部)内附后形成的军事集团。从蔚州、朔州振起到河东节度使李克用为标志,以代北武人(沙陀+汉化胡人+边地汉将)为核心,五代中之唐、晋、汉、周(晋汉周)及北汉皆其分支所建。",
     "五代中原政权的统治核心。沙陀集团把持中原达半个多世纪,深刻塑造了10世纪北方政治格局。",
     ["李克用", "李存勖", "李嗣源", "石敬瑭", "刘知远", "郭威", "柴荣", "刘崇"],
     "880s-960s"),
    ("f_guanlong", "关陇集团", "regional", (530, None), (755, None), "pl_guanzhong",
     "北魏末六镇之乱后,以宇文泰为首、武川镇军人集团为核心的军政势力。以八柱国十二大将军体系为骨架,通过府兵制和赐姓胡化(及汉化)联结胡汉,出过北周、隋、唐三代皇室,主导中国近三百年。",
     "陈寅恪所谓'关陇集团',是中国中古史最具决定性的政治军事集团之一。其影响在唐代衰落,五代时仅余残绪。",
     ["宇文泰", "杨坚", "李虎(唐太祖)", "独孤信", "李弼"],
     "西魏-隋-唐盛期"),
    ("f_heshuo", "河朔三镇", "military_clan", (763, None), (929, None), "pl_hebei",
     "安史之乱后形成的魏博、成德、卢龙三藩镇割据势力。父死子继、自署官吏、贡赋不入。河朔藩镇模式为五代藩镇割据之滥觞。",
     "晚唐'藩镇割据'的典型,深刻影响了五代十国的政治生态。后唐李嗣源即出于此系统。",
     ["田承嗣", "李宝臣", "李怀仙"],
     "代宗-后唐"),
    ("f_zhuwen_group", "朱温集团", "military_clan", (880, None), (923, None), "pl_kaifeng",
     "黄巢旧部投降唐朝后,以朱温(全忠)为首、宣武镇为基地形成的军政集团。吸收大量黄巢降将和河南方镇,后梁立国的核心班底。",
     "五代后梁的政权基础。",
     ["朱温", "朱友贞", "敬翔", "张全义", "葛从周"],
     "唐末-后梁"),
    ("p_yangwu_group", "杨吴集团", "military_clan", (880, None), (937, None), "pl_jianghuai",
     "杨行密奠基的江淮军政集团。以庐州系武人+扬州文官为核心,平定孙儒、田頵等势力,统领淮南、江西。后由徐温、徐知诰(李昪)接掌,转化为南唐。",
     "杨吴-南唐政权的政权基础,五代南方最大势力之一。",
     ["杨行密", "徐温", "徐知诰", "李昪"],
     "唐末-杨吴"),
    ("f_nantang_faction", "南唐党争", "political", (943, None), (975, None), "pl_jinling",
     "南唐中后期,以宋齐丘、冯延巳、孙晟等为代表的朝堂党争。南北士人矛盾激烈。",
     "消耗了南唐的政治能量,反映南方政权内耗。",
     ["宋齐丘", "冯延巳", "孙晟", "韩熙载"],
     "中主-后主时期"),
    ("f_qian_group", "吴越钱氏集团", "military_clan", (875, None), (978, None), "pl_hangzhou",
     "钱镠奠基,以两浙武人+本地士人+海贸商人组成的军政集团。修海塘、兴水利、保境安民。",
     "吴越国的政权基础,贡献于东南经济发展。",
     ["钱镠", "钱元瓘", "钱弘俶"],
     "唐末-北宋初"),
    ("f_eunuch_tang", "晚唐宦官集团", "eunuch", (750, None), (905, None), "pl_chang_an",
     "晚唐以神策军中尉、枢密使为核心的宦官势力,专废立之权。朱温尽诛宦官(900s)而终结。",
     "晚唐政治关键角色,五代式微。",
     ["仇士良", "田令孜", "杨复恭"],
     "中晚唐"),
    ("f_literati_5d", "五代文人圈", "scholarly", (900, None), (979, None), "pl_kaifeng",
     "五代乱世中以冯道为代表的实用主义文官群体。历仕多朝,主持刻九经,保存文化典籍。",
     "五代乱世文脉存续的载体,虽后世争议其节,但客观贡献于文化传承。",
     ["冯道", "和凝", "李崧"],
     "五代全期"),
    ("f_khitan", "契丹(辽)势力", "ethnic", (900, None), (979, None), "pl_liaoshangjing",
     "耶律阿保机统一的草原帝国,深度介入中原事务。947 年灭后晋,长期占有燕云十六州。",
     "10 世纪中国北方最大的外部势力,与五代政权深度纠缠。",
     ["耶律阿保机", "耶律德光", "述律平"],
     "五代全期"),
]


def gen_factions():
    for tup in FACTIONS:
        fid, name, nature, founded, dissolved, region, desc, sig, members, peak = tup
        obj = {
            "id": fid, "type": "Faction", "name": name, "nature": nature,
        }
        if founded and founded[0] is not None:
            d = {"year": founded[0]}
            if founded[1] is not None:
                d["month"] = founded[1]
            obj["founded"] = d
        if dissolved and dissolved[0] is not None:
            d = {"year": dissolved[0]}
            if dissolved[1] is not None:
                d["month"] = dissolved[1]
            obj["dissolved"] = d
        obj["core_region"] = region
        obj["description"] = desc
        obj["significance"] = sig
        obj["core_members"] = members
        obj["peak_period"] = peak
        obj["sources"] = [
            "陈寅恪·唐代政治史述论稿", "新五代史", "旧五代史",
            "谷川道雄·隋唐帝国形成史论", "毛汉光·中国中古政治史论"
        ]
        write(DATA / "entities" / "factions" / f"{fid[2:]}.yaml", obj)


# ============================================================
# BATTLES — 战役
# ============================================================
BATTLES = [
    ("b_boxiang", "柏乡之战", (910, 12), (911, 1), "pl_boxiang", ["k_houliang", "k_houdong_pre"],
     ["p_zhuwen", "p_licunxu"], "k_houdong_pre", "p_licunxu",
     "后梁太祖开平四年至乾化元年。朱温遣王景仁率军攻成德王镕,晋王李存勖、赵王王镕联军迎战。晋军以少胜多,大破梁军主力,后梁河北战略受挫,后唐崛起关键战役。",
     "后梁由盛转衰、晋(后唐)由弱转强的转折点。", ["资治通鉴·卷267-268", "旧五代史·梁书"]),

    ("b_lizhou", "潞州之战", (907, 5), (908, 5), "pl_lizhou", ["k_houliang", "k_houdong_pre"],
     ["p_zhuwen", "p_likaiqu"], "k_houdong_pre", "p_licunxu",
     "朱温篡唐后,围攻晋所据潞州。李克用病死,子存勖继立,设奇兵解围,梁军大败。李存勖初立之胜。",
     "确立李存勖威望,稳固晋对潞州的控扼。", ["资治通鉴·卷266-268", "旧五代史·武皇纪"]),

    ("b_jiahe", "夹河之战", (917, None), (923, None), "pl_weizhou", ["k_houliang", "k_houdong_pre"],
     ["p_zhuyouzhen", "p_licunxu"], "k_houdong_pre", "p_licunxu",
     "917-923 年晋梁在黄河两岸的长期拉锯。923 年李存勖从郓州突入,直捣汴梁,后梁亡,后唐立。",
     "后唐灭梁的关键阶段,体现李存勖军事天才。", ["资治通鉴·卷270-272", "新五代史·唐本纪"]),

    ("b_yanzhou_liao", "契丹灭后晋", (946, 12), (947, 1), "pl_kaifeng", ["k_houjin", "k_liao"],
     ["p_shizhonggui", "p_yeludeguang"], "k_liao", "p_yeludeguang",
     "946 年契丹太宗耶律德光亲征后晋,在滹沱河之战大败晋军主力。947 年正月入汴梁,俘虏出帝石重贵,后晋亡。耶律德光改国号辽,于汴梁登基。掠掠后北返。",
     "五代重大事件。中原首次完全沦于游牧民族之手(短暂)。刺激刘知远建国后汉。", ["资治通鉴·卷285-287", "辽史·太宗纪"]),

    ("b_gaoping", "高平之战", (954, 3), (954, 5), "pl_gaoping", ["k_houzhou", "k_beihan"],
     ["p_chairong", "p_liuchong"], "k_houzhou", "p_chairong",
     "后周世宗柴荣即位之初,北汉刘崇联合契丹南下。柴荣亲征,在高平大败北汉。柴荣临阵督战,樊爱能、何徽临阵脱逃被斩。",
     "巩固后周世宗地位,提振后周军威。世宗改革军制、整顿禁军的起点。", ["资治通鉴·卷291", "旧五代史·周世宗纪"]),

    ("b_houzhou_nantang", "后周攻南唐", (956, 2), (958, 4), "pl_shouzhou", ["k_houzhou", "k_nantang"],
     ["p_chairong", "p_lijing"], "k_houzhou", "p_chairong",
     "955-958 年后周世宗三征南唐。下寿州、六合破南唐军,南唐去帝号,献江北十四州(庐、舒、蕲、黄等)。", 
     "削弱南唐,使后周国力大增。奠北宋统一基础。", ["资治通鉴·卷292-293", "旧五代史·周世宗纪"]),

    ("b_houzhou_liao", "后周北伐辽", (959, 4), (959, 6), "pl_youzhou", ["k_houzhou", "k_liao"],
     ["p_chairong"], "k_houzhou", "p_chairong",
     "959 年柴荣亲征辽,水陆并进,在宁州、莫州、瀛州连胜,收复瀛、莫、易三州及瓦桥、益津、淤口三关。五月欲取幽州,中途病重班师,六月卒。",
     "几乎收复燕云十六州。世宗之死使北伐中止,是中国古代史一大转折。", ["资治通鉴·卷294", "旧五代史·周世宗纪"]),

    ("b_song_jingnan", "宋平荆南", (963, 1), (963, 3), "pl_jiangling", ["k_song", "k_jingnan"],
     ["p_zhaokuangyin"], "k_song", "p_zhaokuangyin",
     "北宋慕容延钊、李处耘率军假道灭荆南。荆南高继冲降。",
     "宋统一战争序幕。", ["续资治通鉴长编·卷4"]),

    ("b_song_houshu", "宋灭后蜀", (964, 11), (965, 2), "pl_chengdu", ["k_song", "k_houshu"],
     ["p_zhaokuangyin", "p_mengchang"], "k_song", "p_zhaokuangyin",
     "宋太祖遣王全斌、刘光义分道伐蜀,66 天灭之。孟昶降。",
     "北宋统一重要一步。", ["续资治通鉴长编·卷5-6", "宋史·太祖本纪"]),

    ("b_song_nanhan", "宋灭南汉", (970, 9), (971, 2), "pl_guangzhou", ["k_song", "k_nanhan"],
     ["p_zhaokuangyin", "p_liuchang"], "k_song", "p_zhaokuangyin",
     "潘美率军攻南汉,在韶州大破南汉象阵。971 年攻至广州,刘鋹降。",
     "岭南归入宋。", ["续资治通鉴长编·卷11-12"]),

    ("b_song_nantang", "宋灭南唐", (974, 9), (976, 1), "pl_jinling", ["k_song", "k_nantang"],
     ["p_zhaokuangyin", "p_liyu"], "k_song", "p_zhaokuangyin",
     "曹彬、潘美率十万大军,自荆南沿江东下。975 年破金陵,李煜降。曹彬不杀一人入城。",
     "南方最大政权归宋,统一大势定。", ["续资治通鉴长编·卷14-17", "宋史·曹彬传"]),

    ("b_song_beihan", "宋灭北汉", (979, 2), (979, 6), "pl_taiyuan", ["k_song", "k_beihan"],
     ["p_liujiyuan"], "k_song", None,
     "宋太宗赵光义亲征,击溃契丹援军,围攻太原。刘继元出降,北汉亡。十国最后结束。",
     "结束五代十国分裂,基本统一中国本部。", ["续资治通鉴长编·卷20", "宋史·太宗本纪"]),
]


def gen_battles():
    # polity aliases used in BATTLES — map them
    polity_aliases = {"k_houdong_pre": "k_houdong"}  # 后唐前身(晋)
    for tup in BATTLES:
        bid, name, date, end, place, combatants, commanders, victor, victor_cmd, desc, sig, srcs = tup
        obj = {
            "id": bid, "type": "Battle", "name": name,
            "date": {"year": date[0], "month": date[1]} if date[0] else None,
            "location": place,
            "combatants": [polity_aliases.get(c, c) for c in combatants],
            "commanders": commanders,
            "victor": polity_aliases.get(victor, victor) if victor else None,
            "victor_commander": victor_cmd if victor_cmd else None,
            "description": desc,
            "significance": sig,
            "sources": srcs,
        }
        if end and end[0] and end != date:
            obj["end_date"] = {"year": end[0], "month": end[1]}
        # remove None values
        obj = {k: v for k, v in obj.items() if v is not None}
        obj["type"] = "Battle"
        obj["id"] = bid
        write(DATA / "entities" / "battles" / f"{bid[2:]}.yaml", obj)


# ============================================================
# EVENTS — 政治/制度事件
# ============================================================
EVENTS = [
    ("e_zhuwen_tang", "朱温代唐", (907, 4), "succession", "pl_kaifeng", ["k_houliang"],
     "907 年朱温逼唐哀帝禅让,建国号梁。唐亡。中国进入五代十国时期。",
     "五代十国之始,标志唐朝正式结束。", ["旧五代史·梁太祖纪", "资治通鉴·卷266"]),

    ("e_yedu_mutiny", "邺都之变 / 兴教门之变", (926, 5), "coup", "pl_luoyang", ["k_houdong"],
     "926 年邺都兵变,李嗣源被军士拥立。庄宗李存勖自洛阳出征,伶人郭从谦发动兴教门之变,弑庄宗。李嗣源入继,是为明宗。",
     "后唐转折。明宗时代为五代少有的治世。", ["资治通鉴·卷274", "新五代史·伶官传"]),

    ("e_shi_jie_liao", "石敬瑭借契丹灭后唐", (936, 11), "coup", "pl_taiyuan", ["k_houjin", "k_houdong"],
     "936 年石敬瑭反,求援于契丹。耶律德光率军入援,败唐军于晋阳。石敬瑭称帝,建国号晋,自称儿皇帝,割燕云十六州。后唐末帝自焚,后唐亡。",
     "燕云十六州丢失,北方屏障尽失。中原数百年受制于游牧民族。", ["资治通鉴·卷280", "旧五代史·晋高祖纪"]),

    ("e_guo_weizhou", "郭威建后周", (950, 12), "coup", "pl_kaifeng", ["k_houhan", "k_houzhou"],
     "950 年后汉隐帝欲杀郭威,反激起郭威兵变。郭威南下,隐帝为乱兵所杀。951 年郭威代汉建周。",
     "五代最后一次改朝换代。后周为北宋统一奠基。", ["资治通鉴·卷289-290", "旧五代史·周太祖纪"]),

    ("e_chenqiao", "陈桥兵变", (960, 2), "coup", "pl_kaifeng", ["k_houzhou", "k_song"],
     "960 年后周殿前都点检赵匡胤在陈桥驿被部下'黄袍加身',回师汴梁,恭帝禅位,建国号宋。",
     "结束五代,中国重新走向统一。", ["续资治通鉴长编·卷1", "宋史·太祖本纪"]),

    ("e_yanyun", "割燕云十六州", (936, 11), "treaty", "pl_youzhou", ["k_houjin", "k_liao"],
     "936 年石敬瑭割让燕云十六州(幽、蓟、瀛、莫、涿、檀、顺、新、妫、儒、武、云、应、寰、朔、蔚)予契丹。中原北方屏障尽失,直到明初(1368)才由徐达、常遇春收复。",
     "中国古代史最大地缘事件之一,影响 400 余年。", ["资治通鉴·卷280", "辽史·地理志"]),

    ("e_zhou_reform", "周世宗改革", (955, None), "reform", "pl_kaifeng", ["k_houzhou"],
     "955-959 年周世宗柴荣推行全面改革:整军(高平之战后裁汰老弱)、均田、灭佛(显德二年)、修水利、扩汴京。",
     "五代最重要的改革,直接为北宋统一提供物质基础。", ["资治通鉴·卷292-294", "旧五代史·周世宗纪"]),

    ("e_zhou_buddhism", "周世宗毁佛", (955, None), "religion", "pl_kaifeng", ["k_houzhou"],
     "955 年周世宗下诏废寺院 30336 所,仅留 2694 所;铜佛铸钱。僧尼归俗者众。",
     "三武一宗灭佛之末。短期内增加国家铜源和人口。", ["资治通鉴·卷292", "佛祖统纪"]),

    ("e_liao_kingdom", "契丹建国", (916, None), "other", "pl_liaoshangjing", ["k_liao"],
     "916 年耶律阿保机称帝,国号契丹。947 年耶律德光改国号辽。",
     "北方草原进入国家形态,长期影响中原。", ["辽史·太祖纪"]),

    ("e_jingnan_peace", "吴越纳土归宋", (978, 5), "diplomacy", "pl_hangzhou", ["k_wuyue", "k_song"],
     "978 年吴越国王钱弘俶献两浙十三州一军八十六县于宋,和平归附。避免一场大战。",
     "中国和平统一的早期范例。", ["续资治通鉴长编·卷19", "宋史·吴越钱氏"]),
]


def gen_events():
    for tup in EVENTS:
        eid, name, date, category, place, polities, desc, impact, srcs = tup
        obj = {
            "id": eid, "type": "Event", "name": name,
            "date": {"year": date[0]} if date[0] else None,
            "category": category,
            "location": place,
            "polities_involved": polities,
            "description": desc,
            "impact": impact,
            "sources": srcs,
        }
        if date[0] and date[1]:
            obj["date"] = {"year": date[0], "month": date[1]}
        # clean None
        obj = {k: v for k, v in obj.items() if v is not None}
        obj["type"] = "Event"
        obj["id"] = eid
        write(DATA / "entities" / "events" / f"{eid[2:]}.yaml", obj)


if __name__ == "__main__":
    print(f"→ generating factions, battles, events to {DATA}/entities/")
    gen_factions()
    print(f"  ✓ {len(FACTIONS)} factions")
    gen_battles()
    print(f"  ✓ {len(BATTLES)} battles")
    gen_events()
    print(f"  ✓ {len(EVENTS)} events")
