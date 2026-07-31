#!/usr/bin/env python3
"""修全库内嵌外键:70 处悬空 + 23 处类型不符。

背景:validate_data.py 只查 relations/*.yaml 两端,从不查实体内嵌的外键
(person.birthplace / polity.capital / event.polities_involved ...)。于是这些
引用指向虚空多年而 errors=0。本脚本修数据,配套的验证器补洞见 validate_data.py。

三类成因,分别处理:
1. id 漂移 —— 存者在库,只是写法不一(p_caopi vs p_cao_pi)。改引用。
2. 类型不符 —— 字段声明 to: Polity,值却是 Dynasty(k_xixia.ended_by → d_yuan)。
   同名的 Polity 都在,改指过去。Polity/Dynasty 同名并存 12 组是另一个结构问题
   (d_song 罩 k_beisong+k_nansong 是合理层级;d_jin_jurchen 与 k_jin 起止全同是冗余),
   不在本脚本范围。
3. 实体从未建 —— `_pre` 是一套没写完的约定:指政权正式立国前的军政集团
   (曹操 192-220 是汉丞相,曹魏 220 才立国)。引用先写了,实体没建。本脚本补建。

另修两处史实错误(见 FACTUAL 段注释)。
"""
import yaml, glob, pathlib, sys, collections

# ── 1+2. 引用改指:bad id → good id ────────────────────────────────────────
RENAME = {
    # id 漂移
    "p_caopi":         "p_cao_pi",
    "p_wanyan_aguda":  "p_wanyanaguda",
    "p_sunzhongshan":  "p_sun_zhongshan",
    "p_libian":        "p_li_bian",
    "p_yuwen_tai_pre": "p_yuwentai",
    "p_kublai":        "p_hubilai",
    "pl_daxing_sui":   "pl_daxing",
    "pl_huining_jin":  "pl_huining_wya",
    "k_jin_jurchen":   "k_jin",
    "k_tang_pre":      "k_tang",
    "d_tang_pre":      "k_tang",
    "d_sui_pre":       "k_sui",
    "d_donghan":       "k_donghan",
    # 隋.ended_by_person: p_yuangungong 是个伪造 id。隋档自述「618 炀帝被弑,隋亡」,
    # 弑炀帝者宇文化及(江都之变),库中有 p_yuwen_huaji。
    "p_yuangungong":   "p_yuwen_huaji",
    # 类型不符:声明 to: Polity,值是 Dynasty
    "d_yuan":          "k_yuan",
    "d_sui":           "k_sui",
    "d_qing":          "k_qing",
    # 新建实体用规范 id,原引用里的怪 id 一并改过来
    "k_rib":           "k_riben",
    "k_ying":          "k_britain",
    "k_waci":          "k_waci",          # 保持(本就可读)
    "p_xianxian_waci": "p_yexian",
    "p_itou_rit":      "p_ito_sukeyuki",
    "k_wu_zhang":      "k_wu_zhu",        # 吴 = 朱元璋政权,原 id 易读成张士诚
    "k_ranwei_pre":    "k_ranwei",        # 冉魏是十六国之一,不是谁的「前身」
    "k_hou_qin_pre":   "k_houqin",
}

# ── 史实修正(非改名,是改错) ───────────────────────────────────────────────
FACTUAL = {
    # 西晋 316 亡于刘曜的前赵(汉赵);东晋是继承者,不是终结者。
    ("k_xijin", "ended_by"): ("k_dongjin_pre", "k_hanzhao"),
    # 白马驿之祸(905)时朱温尚为唐臣,后梁 907 才立。涉事政权是唐。
    ("e_baima_yi", "polities_involved"): ("k_houliang_pre", "k_tang"),
    # 明取代的是元本身。
    ("k_ming", "supplanted"): ("k_yuan_pre", "k_yuan"),
}
# 鄱阳湖之战(1363)是朱元璋灭陈友谅,元不是交战方 —— 从 combatants 删除。
DROP = {("b_poyanghu", "combatants"): "k_yuan_pre"}

# ── 3. 补建实体 ──────────────────────────────────────────────────────────
PERSONS = [
  dict(id="p_yuanchonghuan", name="袁崇焕", courtesy_name="元素", born={"year":1584}, died={"year":1630,"month":8},
       gender="male", roles=["general"], importance=2, birthplace="pl_dongguan_yuan",
       bio="明末蓟辽督师。1626 宁远之战以红夷大炮却后金军,为明军首胜;1627 宁锦大捷。"
           "1629 己巳之变后金绕道入关直逼北京,崇祯以通敌罪下其狱,1630 年八月磔于西市。",
       sources=["明史·袁崇焕传","国榷"]),
  dict(id="p_dingruchang", name="丁汝昌", courtesy_name="禹廷", born={"year":1836}, died={"year":1895,"month":2},
       gender="male", roles=["general"], importance=2, birthplace="pl_lujiang_ding",
       bio="北洋水师提督。1894 年九月十七日黄海海战率舰队与日本联合舰队鏖战五小时,负伤不退。"
           "1895 年二月威海卫被围,援绝,拒降服毒死。",
       sources=["清史稿·丁汝昌传","东方兵事纪略"]),
  dict(id="p_yexian", name="也先", alias=["額森"], died={"year":1454}, gender="male",
       roles=["ruler","general"], importance=2,
       bio="瓦剌太师,脱欢之子。1449 土木堡之变俘明英宗,进围北京为于谦所败。"
           "1453 自立为大元天圣大可汗 —— 非成吉思汗黄金家族而称汗,故诸部不服。1454 为部下阿剌知院所杀。",
       sources=["明史·瓦剌传","明英宗实录"]),
  dict(id="p_yanghao", name="杨镐", died={"year":1629}, gender="male", roles=["official","general"], importance=3,
       bio="明辽东经略。1619 萨尔浒之战以四路分兵进剿后金,努尔哈赤「凭尔几路来,我只一路去」各个击破,"
           "明军三路覆没。下狱十年,1629 伏诛。",
       sources=["明史·杨镐传","明神宗实录"]),
  dict(id="p_ito_sukeyuki", name="伊东祐亨", born={"year":1843}, died={"year":1914}, gender="male",
       roles=["general"], importance=3,
       bio="日本海军中将,联合舰队司令长官。1894 黄海海战、1895 威海卫之役日方指挥官。",
       sources=["清史稿·邦交志","东方兵事纪略"]),
  dict(id="p_ranmin", name="冉闵", died={"year":352,"month":5}, gender="male", roles=["ruler","general"], importance=3,
       bio="后赵石虎养孙。350 灭后赵自立,国号魏(史称冉魏),颁杀胡令,邺城胡羯死者以十万计。"
           "352 为前燕慕容恪所擒,斩于遏陉山。",
       sources=["晋书·载记第七","资治通鉴·卷98-99"]),
  dict(id="p_yaochang", name="姚苌", courtesy_name="景茂", born={"year":330}, died={"year":393},
       gender="male", roles=["ruler"], importance=3,
       bio="羌族,姚弋仲之子。原为前秦将,淝水战后 384 自立,称万年秦王,国号秦(史称后秦)。385 缢杀苻坚于新平。",
       sources=["晋书·载记第十六","资治通鉴·卷105-108"]),
  dict(id="p_maodun", name="冒顿单于", died={"year":-174}, gender="male", roles=["ruler"], importance=2,
       bio="前209 以鸣镝弑父头曼自立。东破东胡、西走月氏、南并楼烦白羊,控弦之士三十余万,"
           "匈奴由此臻于极盛。前200 白登之围困刘邦七日。",
       sources=["史记·匈奴列传","汉书·匈奴传"]),
]

def poly(id, name, name_en, color, f, e, desc, src, **kw):
    d = dict(id=id, type="Polity", name=name, name_en=name_en, color=color,
             founded=f, ended=e, description=desc, sources=src)
    d.update(kw); return d

POLITIES = [
  # 军政集团:奉汉正朔,未立国号。作为交战方存在,故建为 Polity;起止取其作为
  # 独立军政实体的存续期,description 写明其非独立政权 —— 这一分野目前只能靠
  # 文字承载,Polity 无「立国/集团」字段(见 WORKLOG,与 Polity/Dynasty 冗余同批待议)。
  poly("k_caowei_pre","曹操集团","Cao Cao's Faction","#8b5a3c",{"year":192},{"year":220,"month":10},
       "192 曹操领兖州牧起家,196 迎献帝都许,挟天子以令诸侯。官渡破袁绍、平河北,爵至魏王。"
       "终其身奉汉正朔未称帝,220 曹丕代汉建魏,此集团转为曹魏政权。",
       ["三国志·魏书·武帝纪"], founder="p_cao_cao"),
  poly("k_shuhan_pre","刘备集团","Liu Bei's Faction","#c0654a",{"year":194},{"year":221,"month":4},
       "194 刘备领徐州牧起,辗转依吕布、曹操、袁绍、刘表。208 赤壁后取荆南、入益州,219 进位汉中王。"
       "221 称帝建汉(史称蜀汉),此集团转为蜀汉政权。",
       ["三国志·蜀书·先主传"], founder="p_liu_bei"),
  poly("k_dongwu_pre","孙权集团","Sun Quan's Faction","#4a7c6f",{"year":195},{"year":229,"month":4},
       "195 孙策渡江略地,200 孙权继位据江东六郡。208 赤壁破曹,222 称吴王。"
       "229 称帝建吴,此集团转为东吴政权。",
       ["三国志·吴书·吴主传"], founder="p_sun_quan"),
  poly("k_yuanshao_pre","袁绍集团","Yuan Shao's Faction","#7a6a9c",{"year":191},{"year":207,"month":9},
       "191 袁绍夺冀州,后并青、并、幽,据河北四州,为汉末最强诸侯。200 官渡败于曹操,202 忧愤死。"
       "207 曹操定辽东,袁尚袁熙授首,集团覆灭。",
       ["三国志·魏书·袁绍传"], founder="p_yuan_shao", ended_by="k_caowei_pre"),
  # 十六国:是真政权,原 id 的 _pre 后缀是误标
  poly("k_ranwei","冉魏","Ran Wei","#9c4a4a",{"year":350,"month":1},{"year":352,"month":4},
       "350 冉闵灭后赵自立,国号魏,都邺。颁杀胡令,邺城胡羯死者以十万计,"
       "羯人几近族灭 —— 十六国最惨烈的族群屠杀之一。352 为前燕所灭,立国二年。",
       ["晋书·载记第七","资治通鉴·卷98-99"], founder="p_ranmin", capital="pl_yecheng"),
  poly("k_houqin","后秦","Later Qin","#6a8c4a",{"year":384,"month":4},{"year":417,"month":8},
       "384 淝水战后姚苌自立,国号秦,都长安,羌族政权。385 缢杀苻坚灭前秦。"
       "417 东晋刘裕北伐,姚泓出降,国亡。",
       ["晋书·载记第十六至十八","资治通鉴·卷105-118"], founder="p_yaochang", capital="pl_chang_an"),
  # 北族与域外政权
  poly("k_xiongnu","匈奴","Xiongnu","#8c7a4a",{"year":-209},{"year":48},
       "前209 冒顿单于弑父自立,控弦三十余万,与汉相持百余年。前200 白登之围后汉行和亲;"
       "武帝三伐(河南、河西、漠北)后匈奴远遁。48 分裂为南北匈奴:南匈奴附汉,"
       "北匈奴 91 年为汉所破而西迁。此处起止取其作为统一政权的存续期。",
       ["史记·匈奴列传","汉书·匈奴传"], founder="p_maodun"),
  poly("k_waci","瓦剌","Oirat","#6a8ca0",{"year":1438},{"year":1454},
       "蒙古西部部族联盟(卫拉特)。1438 脱欢统一漠北、立脱脱不花为可汗而己为太师,实权在瓦剌。"
       "子也先 1449 土木堡俘明英宗,1453 自立为汗,1454 被杀,联盟瓦解。"
       "此处起止取其作为统一政治势力的活跃期;部族本身此前此后皆延续,后裔演为准噶尔。",
       ["明史·瓦剌传","明英宗实录"], founder="p_yexian"),
  poly("k_riben","日本","Empire of Japan","#a0616a",{"year":1868},{"year":1947,"month":5},
       "明治维新后的近代日本国家。1894 甲午战争败清、割台湾,1905 日俄战争后据南满,"
       "1910 并朝鲜,1931 侵占东北,1937 全面侵华。1945 战败,1947 新宪法施行。",
       ["清史稿·邦交志三·日本","日本国志(黄遵宪)"]),
  poly("k_britain","英国","United Kingdom","#4a6a9c",{"year":1801,"month":1},{"year":1922,"month":12},
       "大不列颠及爱尔兰联合王国。1840 以鸦片贸易受阻为由发动战争,迫清签《南京条约》割香港、开五口,"
       "为近代不平等条约体系之始;1856 偕法国再启第二次鸦片战争,1860 焚圆明园。",
       ["清史稿·邦交志一·英吉利","筹办夷务始末"]),
  # 元末割据
  poly("k_wu_zhu","吴(朱元璋)","Wu (Zhu Yuanzhang)","#b08a3c",{"year":1356,"month":3},{"year":1368,"month":1},
       "1356 朱元璋取集庆改应天府,奉韩林儿龙凤年号,1361 封吴国公,1364 自立吴王(史称西吴,"
       "以别于张士诚之东吴)。1363 鄱阳湖灭陈友谅,1367 灭张士诚,1368 称帝建明。",
       ["明史·太祖本纪"], founder="p_zhuyuanzhang", capital="pl_nanjing_ming"),
  poly("k_han_chen","汉(陈友谅)","Han (Chen Youliang)","#a04a4a",{"year":1360,"month":5},{"year":1364,"month":2},
       "1360 陈友谅弑徐寿辉称帝,国号汉,都江州,据湖广江西,为元末最强割据势力。"
       "1363 鄱阳湖决战中箭死,1364 子陈理降朱元璋。",
       ["明史·陈友谅传"], founder="p_chenyouliang", ended_by="k_wu_zhu"),
]

PLACES = [
  dict(id="pl_jiangnan", type="Place", name="江南", modern_name="长江下游以南地区",
       province="江苏/浙江/江西/安徽", latitude=30.5, longitude=119.5, category="region",
       description="长江下游以南。宋室南渡后为经济文化重心,理学诸派(闽学、江西心学、浙东)皆兴于此。",
       sources=["宋史·地理志"]),
  dict(id="pl_jinxi_fuzhou", type="Place", name="金溪", modern_name="金溪县", province="江西",
       latitude=27.9, longitude=116.76, category="city",
       description="抚州金溪。陆九渊籍贯。",
       sources=["宋史·陆九渊传","宋史·地理志"]),
  dict(id="pl_dongguan_yuan", type="Place", name="东莞", modern_name="东莞", province="广东",
       latitude=23.02, longitude=113.75, category="city",
       description="袁崇焕籍贯(《明史》作东莞,另有广西藤县一说,今两地皆有其祠)。",
       sources=["明史·袁崇焕传"]),
  dict(id="pl_lujiang_ding", type="Place", name="庐江", modern_name="庐江县", province="安徽",
       latitude=31.25, longitude=117.29, category="city",
       description="丁汝昌籍贯。", sources=["清史稿·丁汝昌传"]),
]
# 陆九渊籍贯原指 pl_jinjiang_lu(不存在)。库中 pl_jinjiang_lv 是福建晋江,与江西金溪
# 非一地,不可并 —— 故另建 pl_jinxi_fuzhou。
RENAME["pl_jinjiang_lu"] = "pl_jinxi_fuzhou"

# ── 执行 ────────────────────────────────────────────────────────────────
schemas = {}
for f in glob.glob("schema/*.yaml"):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("type") and "fields" in d:
        r = {}
        for k, v in (d["fields"] or {}).items():
            if not isinstance(v, dict): continue
            if v.get("type") == "ref" and v.get("to"): r[k] = (v["to"], False)
            elif v.get("type") == "array" and isinstance(v.get("items"), dict) \
                 and v["items"].get("type") == "ref" and v["items"].get("to"): r[k] = (v["items"]["to"], True)
        schemas[d["type"]] = r

files, ents = {}, {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"):
        ents[d["id"]] = d; files[d["id"]] = f

DIRS = {"Person": "persons", "Polity": "polities", "Place": "places"}
new = [(p, "Person") for p in PERSONS] + [(p, "Polity") for p in POLITIES] + [(p, "Place") for p in PLACES]

# 护栏:新建实体的 id 不得与现有冲突;其自身的 ref 字段必须落在实存实体上
# (此前三次凭空猜 id 翻车,故裁定 key 一律先验后用)
created = {d["id"] for d, _ in new}
for d, t in new:
    if d["id"] in ents:
        sys.exit(f"✗ 新建 id 已存在:{d['id']}")
    d.setdefault("type", t)
    for fld, (to, arr) in schemas.get(t, {}).items():
        v = d.get(fld)
        for x in ([v] if v and not arr else (v or [])):
            if isinstance(x, str) and x not in ents and x not in created:
                sys.exit(f"✗ 新建 {d['id']}.{fld} 指向不存在的 {x}")
for bad, good in RENAME.items():
    if good not in ents and good not in created:
        sys.exit(f"✗ 改指目标不存在:{bad} → {good}")
for (eid, fld), (bad, good) in FACTUAL.items():
    if eid not in ents: sys.exit(f"✗ 史实修正的实体不存在:{eid}")
    if good not in ents and good not in created: sys.exit(f"✗ 史实修正目标不存在:{good}")

def dump(d, path):
    yaml.safe_dump(d, open(path, "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False, width=200)

n_new = 0
for d, t in new:
    p = f"data/entities/{DIRS[t]}/{d['id'].split('_',1)[1]}.yaml"
    if not pathlib.Path(p).exists():
        dump(d, p); ents[d["id"]] = d; files[d["id"]] = p; n_new += 1

# 只改 schema 声明过的 ref 字段 —— 全局文本替换会把 d_yuan 实体自身也改坏
stat = collections.Counter()
for i, d in list(ents.items()):
    if i in created: continue
    changed = False
    for fld, (to, arr) in schemas.get(d.get("type"), {}).items():
        if fld not in d or d[fld] is None: continue
        if (i, fld) in FACTUAL:
            bad, good = FACTUAL[(i, fld)]
            if arr and bad in d[fld]:
                d[fld] = [good if x == bad else x for x in d[fld]]; changed = True; stat["史实修正"] += 1
            elif not arr and d[fld] == bad:
                d[fld] = good; changed = True; stat["史实修正"] += 1
        if (i, fld) in DROP and arr and DROP[(i, fld)] in d[fld]:
            d[fld] = [x for x in d[fld] if x != DROP[(i, fld)]]; changed = True; stat["删错误交战方"] += 1
        vals = d[fld] if arr else [d[fld]]
        out = []
        for x in vals:
            if isinstance(x, str) and x in RENAME and RENAME[x] != x:
                out.append(RENAME[x]); changed = True; stat["改指"] += 1
            else: out.append(x)
        d[fld] = out if arr else out[0]
    if changed: dump(d, files[i])

print(f"新建实体 {n_new}(人 {len(PERSONS)} / 政权 {len(POLITIES)} / 地点 {len(PLACES)});" +
      "".join(f" {k} {v};" for k, v in stat.items()))
