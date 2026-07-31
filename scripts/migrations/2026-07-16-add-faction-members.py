#!/usr/bin/env python3
"""补建 32 个人物 —— Faction.core_members 里点名却在库中无实体者。

来由:core_members 存的是人名字符串,从没人查过这些人在不在库里。查了才发现 35 个
名字中 32 个查无此人(另 2 个是「朱温(降唐前)」「李虎(唐太祖)」——带括号注释的既有
人物,1 个是田令孜在两份重复的宦官集团里各出现一次)。

补人是「core_members 迁进 member_of 关系」的前提:先删字段就是丢这 32 个名字。

roles 取值须在 person.yaml 的枚举内(ruler/official 不存在,那是上一轮踩过的坑)。
年份不确定者只写确知的那一端(如「?-893」写 died 不写 born),不编造。
"""
import yaml, pathlib, glob, sys

def P(id, name, **kw):
    return dict(id=id, type="Person", name=name, gender=kw.pop("gender", "male"), **kw)

PEOPLE = [
  # ── 东林党 ──
  P("p_guxiancheng", "顾宪成", courtesy_name="叔时", born={"year":1550}, died={"year":1612},
    roles=["scholar","civil_official"], importance=3,
    bio="无锡人。1594 削籍归里,与弟允成修复东林书院讲学,议论朝政人物,天下士大夫遥相应和,"
        "「东林党」之名由是起。其讲堂联「风声雨声读书声声声入耳,家事国事天下事事事关心」。",
    sources=["明史·顾宪成传","东林书院志"]),
  P("p_yanglian", "杨涟", courtesy_name="文孺", born={"year":1572}, died={"year":1625,"month":7},
    roles=["civil_official"], importance=2,
    bio="应山人。1620 红丸、移宫两案中力争,声名大起。1624 上疏劾魏忠贤二十四大罪,"
        "反被诬受熊廷弼贿,下诏狱。狱中受土囊压身、铁钉贯耳之酷,1625 年七月死。",
    sources=["明史·杨涟传","碧血录"]),
  P("p_gaopanlong", "高攀龙", courtesy_name="存之", born={"year":1562}, died={"year":1626,"month":3},
    roles=["civil_official","scholar"], importance=3,
    bio="无锡人,东林书院与顾宪成并称「顾高」。1626 阉党缉捕东林诸人,攀龙夜赋绝命词后投池自尽。",
    sources=["明史·高攀龙传","东林书院志"]),
  # ── 阉党 ──
  P("p_cuichengxiu", "崔呈秀", died={"year":1627,"month":11},
    roles=["civil_official"], importance=3,
    bio="阉党「五虎」之首,魏忠贤谋主。因贪贿被劾,投魏忠贤为养子得免,遂力劝魏兴大狱杀东林诸人。"
        "1627 崇祯即位,魏忠贤失势,呈秀自缢,戮尸。",
    sources=["明史·崔呈秀传"]),
  # ── 晚唐宦官 ──
  P("p_tianlingzi", "田令孜", died={"year":893},
    roles=["eunuch"], importance=3,
    bio="唐僖宗时神策军中尉,僖宗呼为「阿父」,政事一决于其手。880 黄巢入长安,挟僖宗奔蜀。"
        "886 又劫僖宗奔宝鸡,天下切齿。后依王建,893 为建所杀。",
    sources=["旧唐书·宦官传","资治通鉴·卷253-259"]),
  P("p_yangfugong", "杨复恭", died={"year":894},
    roles=["eunuch"], importance=3,
    bio="唐昭宗时神策军中尉。拥立昭宗,自谓有定策功,养子数十人分据藩镇,号「外宅郎君」。"
        "892 与昭宗决裂出奔,894 被擒斩。",
    sources=["旧唐书·宦官传","资治通鉴·卷259-260"]),
  P("p_juwenzhen", "俱文珍", died={"year":813},
    roles=["eunuch"], importance=3,
    bio="唐宦官。805 顺宗中风失语,文珍等胁其内禅太子(永贞内禅),王叔文集团的永贞革新百余日而败,"
        "「二王八司马」尽贬。此为宦官废立之权的开端。",
    sources=["旧唐书·宦官传","资治通鉴·卷236"]),
  P("p_wangshoucheng", "王守澄", died={"year":835,"month":10},
    roles=["eunuch"], importance=3,
    bio="唐宦官,历宪、穆、敬、文四朝。820 宪宗暴崩,时议归罪守澄等;其后穆宗、文宗皆由其拥立。"
        "835 文宗与李训、郑注谋诛宦官,先鸩杀守澄,旋即甘露之变事败,宦官反噬。",
    sources=["旧唐书·宦官传","资治通鉴·卷241-245"]),
  # ── 李党 ──
  P("p_zhengtan", "郑覃", died={"year":842},
    roles=["civil_official"], importance=3,
    bio="唐宰相,李德裕党要角。精经学,恶进士浮华,尝请废进士科。文宗时与牛党李宗闵相攻,"
        "为牛李党争核心人物之一。",
    sources=["旧唐书·郑覃传","资治通鉴·卷245-246"]),
  # ── 关陇集团 ──
  P("p_libi", "李弼", born={"year":494}, died={"year":557},
    roles=["general"], importance=3,
    bio="西魏八柱国之一,赐姓徒何氏。沙苑之战为宇文泰破东魏高欢军。曾孙即隋末瓦岗军首领李密。",
    sources=["周书·李弼传","北史"]),
  # ── 河朔三镇 ──
  P("p_luoshaowei", "罗绍威", born={"year":877}, died={"year":910},
    roles=["general"], importance=3,
    bio="魏博节度使。魏博牙军骄横,自田承嗣以来废立主帅百余年。907 绍威借朱温兵尽诛牙军八千家,"
        "牙军之患遂绝 —— 而魏博自此兵弱,绍威亦悔之,谓「合六州四十三县铁,不能为此错」。",
    sources=["旧五代史·罗绍威传","资治通鉴·卷265"]),
  # ── 黄巢起义军 ──
  P("p_mengkai", "孟楷", died={"year":883},
    roles=["rebel_leader","general"], importance=3,
    bio="黄巢部将,尚让之亚。881 黄巢入长安建大齐,楷为尚书左仆射。883 攻蔡州、陈州,为秦宗权部所擒杀,"
        "巢怒而围陈州三百日 —— 「舂磨寨」食人之惨即在此役。",
    sources=["新唐书·黄巢传","资治通鉴·卷255"]),
  # ── 朱温集团 ──
  P("p_gecongzhou", "葛从周", died={"year":914},
    roles=["general"], importance=3,
    bio="朱温麾下第一名将,「山东一条葛」。破朱瑄朱瑾、败李克用、平刘仁恭,"
        "为后梁开国之基。晚年病废,得以善终。",
    sources=["旧五代史·葛从周传"]),
  # ── 契丹 ──
  P("p_shulüping", "述律平", born={"year":879}, died={"year":953,"month":6}, gender="female",
    alias=["应天太后","月理朵"], roles=["consort"], importance=2,
    bio="辽太祖耶律阿保机皇后。有断腕留冢事:阿保机死,诸将请殉,平斩己右腕纳于陵中代己身,"
        "而以此逼杀政敌百余人。926 阿保机死后废长子倍、立次子德光,927 德光即位,是为辽太宗。"
        "947 又欲立幼子李胡,为群臣所拒,遂被幽于祖州。",
    sources=["辽史·后妃传","资治通鉴·卷285-286"]),
  # ── 五代文人圈 ──
  P("p_heningwd", "和凝", courtesy_name="成绩", born={"year":898}, died={"year":955},
    roles=["civil_official","literatus"], importance=3,
    bio="历后梁至后周五朝,后晋时同中书门下平章事。少年好为艳词,时号「曲子相公」;"
        "又撰《疑狱集》,为中国现存最早的案例法书之一。",
    sources=["旧五代史·和凝传","新五代史"]),
  P("p_lisong_wd", "李崧", died={"year":948},
    roles=["civil_official"], importance=3,
    bio="后晋宰相。契丹灭晋后仕辽,后归后汉。948 为苏逢吉挟私诬以谋反,族诛 —— 五代宰辅无善终之典型。",
    sources=["旧五代史·李崧传"]),
  # ── 南唐党争 ──
  P("p_songqiqiu", "宋齐丘", courtesy_name="超回", born={"year":887}, died={"year":959},
    roles=["civil_official"], importance=3,
    bio="南唐开国谋主,佐李昪代吴。后结党擅权,与孙晟、韩熙载等相攻,是为南唐党争。"
        "959 后主李璟数其罪,放归九华山,缢死。",
    sources=["南唐书","十国春秋·南唐"]),
  P("p_fengyansi", "冯延巳", courtesy_name="正中", born={"year":903}, died={"year":960},
    roles=["civil_official","literatus"], importance=3,
    bio="南唐宰相,宋齐丘党。为相无善状,而词冠五代 ——「风乍起,吹皱一池春水」,"
        "上承温韦、下启晏欧,王国维谓其「开北宋一代风气」。",
    sources=["南唐书","阳春集"]),
  P("p_sunsheng", "孙晟", died={"year":956,"month":10},
    roles=["civil_official"], importance=3,
    bio="南唐宰相。956 后周世宗攻淮南,晟奉使乞和,被留。世宗问江南虚实,晟不对,"
        "曰「臣唐大臣,岂可为陛下谋」,遂见杀。",
    sources=["南唐书","新五代史·南唐世家"]),
  P("p_hanxizai", "韩熙载", courtesy_name="叔言", born={"year":902}, died={"year":970},
    roles=["civil_official","literatus"], importance=2,
    bio="北人南奔,仕南唐三世。后主欲相之,熙载知国将亡而不欲当其咎,乃纵情声色以自污。"
        "后主遣画工顾闳中夜窥其宴,归而图之,即《韩熙载夜宴图》。",
    sources=["南唐书·韩熙载传","十国春秋"]),
  # ── 杨吴集团 ──
  P("p_xuwen", "徐温", courtesy_name="敦美", born={"year":862}, died={"year":927,"month":10},
    roles=["general","civil_official"], importance=3,
    bio="杨行密旧将,杨吴权臣。908 弑杨渥,专吴政二十年,封齐国公。养子徐知诰(即李昪)嗣其位,"
        "937 代吴建南唐。",
    sources=["新五代史·吴世家","十国春秋·吴"]),
  # ── 义社十兄弟 ──
  P("p_lijixun", "李继勋", born={"year":916}, died={"year":977},
    roles=["general"], importance=3,
    bio="义社十兄弟中年最长者,后周时官位在赵匡胤之上。宋初为安国军节度使,伐北汉屡为前驱。",
    sources=["宋史·李继勋传"]),
  P("p_wangshenqi", "王审琦", courtesy_name="仲宝", born={"year":925}, died={"year":974},
    roles=["general"], importance=3,
    bio="义社十兄弟之一,与赵匡胤友善。陈桥兵变时为殿前都虞候,与石守信为内应。"
        "961 杯酒释兵权,出为忠正军节度使。",
    sources=["宋史·王审琦传"]),
  P("p_hanzhongyun", "韩重赟", died={"year":974},
    roles=["general"], importance=3,
    bio="义社十兄弟之一。陈桥兵变为控鹤军都指挥使。968 有告其私选亲兵为腹心者,"
        "太祖欲诛之,赵普谏止,乃出为彰德军节度使。",
    sources=["宋史·韩重赟传"]),
  # ── 元祐党人 ──
  P("p_huangtingjian", "黄庭坚", courtesy_name="鲁直", art_name="山谷道人",
    born={"year":1045}, died={"year":1105,"month":9},
    roles=["literatus"], importance=2,
    bio="苏门四学士之一,江西诗派开山。以修《神宗实录》获罪,贬黔州、宜州,卒于贬所。"
        "崇宁元年名列元祐党人碑。书法为宋四家之一。",
    sources=["宋史·黄庭坚传","山谷集"]),
  # ── 南宋主战派 ──
  P("p_zhangjun_song", "张浚", courtesy_name="德远", born={"year":1097}, died={"year":1164,"month":8},
    roles=["civil_official"], importance=2,
    bio="南宋主战派领袖。1130 富平之战集五路兵二十万败于金人,关陕尽失;1163 督师北伐,"
        "符离一溃而隆兴和议成。两度当国、两度丧师,而终身言战不悔 —— 主战派的抱负与其军事才具"
        "之间的落差,南宋无人比他更典型。",
    sources=["宋史·张浚传","建炎以来系年要录"]),
  # ── 明淮西将帅集团 ──
  P("p_tanghe", "汤和", courtesy_name="鼎臣", born={"year":1326}, died={"year":1395,"month":8},
    roles=["general"], importance=3,
    bio="濠州钟离人,与朱元璋同里。最早招元璋入郭子兴军者即汤和。灭方国珍、张士诚,封信国公。"
        "洪武功臣中独得善终 —— 晚年首请归田纳兵权,又暗弱不与政事,故免于胡蓝之狱。",
    sources=["明史·汤和传"]),
  # ── 靖难功臣 ──
  P("p_zhangyu_ming", "张玉", courtesy_name="世美", born={"year":1343}, died={"year":1401,"month":1},
    roles=["general"], importance=3,
    bio="靖难第一名将,燕军谋主。1400 东昌之战,朱棣为盛庸所围,玉率兵入阵求棣,力战死。"
        "棣闻之恸哭,谓「胜负常事,不足虑,恨失玉耳」。子张辅后平安南。",
    sources=["明史·张玉传"]),
  P("p_zhuneng", "朱能", courtesy_name="士弘", born={"year":1370}, died={"year":1406,"month":10},
    roles=["general"], importance=3,
    bio="靖难功臣,与张玉同为燕军柱石。张玉死后独当大任,白沟河、灵璧皆有功,封成国公。"
        "1406 征安南,道卒于军。",
    sources=["明史·朱能传"]),
  # ── 太平天国 ──
  P("p_weichanghui", "韦昌辉", born={"year":1823}, died={"year":1856,"month":11},
    roles=["rebel_leader"], importance=2,
    bio="太平天国北王。1856 奉洪秀全密诏诛东王杨秀清,遂纵兵屠杨氏部属两万余人于天京,"
        "累日不止 —— 天京事变是太平天国由盛转衰的转折,精锐与人心俱尽于自相残杀。"
        "旋因滥杀失众,为洪秀全所杀。",
    sources=["李秀成自述","太平天国史"]),
  # ── 湘军 ──
  P("p_hulinyi", "胡林翼", courtesy_name="贶生", born={"year":1812}, died={"year":1861,"month":9},
    roles=["civil_official","general"], importance=2,
    bio="湖北巡抚,湘军实际的后勤与财政中枢。整顿厘金、漕务以养军,曾国藩谓其才胜己十倍。"
        "1861 安庆克复月余而咯血死。",
    sources=["清史稿·胡林翼传","胡文忠公遗集"]),
  P("p_pengyulin", "彭玉麟", courtesy_name="雪琴", born={"year":1816}, died={"year":1890,"month":4},
    roles=["general"], importance=3,
    bio="湘军水师创建者,与曾国藩、左宗棠并称。历官兵部尚书而屡辞不就,前后辞谢督抚之命六次。"
        "1884 中法战争时年近七十,仍赴广东督师。",
    sources=["清史稿·彭玉麟传"]),
]

# ── 护栏 ────────────────────────────────────────────────────────────────
files, ents = {}, {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"): ents[d["id"]] = d; files[d["id"]] = f

VALID_ROLES = set((((yaml.safe_load(open("schema/person.yaml", encoding="utf-8"))
                     ["fields"].get("roles") or {}).get("items") or {}).get("options")) or [])
# 别名也算命中 —— 徐知诰是李昪的 alias、章炳麟是章太炎的 alias,只比对 name 会
# 把它们误报成「查无此人」而去重复建人。
byname = {}
for d in ents.values():
    if d.get("type") != "Person": continue
    for n in [d.get("name")] + list(d.get("alias") or []):
        if n: byname.setdefault(n, []).append(d["id"])

for p in PEOPLE:
    if p["id"] in ents: sys.exit(f"✗ id 已存在:{p['id']}")
    if p["name"] in byname: sys.exit(f"✗ 同名人物已在库:{p['name']} = {byname[p['name']]}")
    bad = set(p.get("roles") or []) - VALID_ROLES
    if bad: sys.exit(f"✗ {p['name']} roles 不在枚举内:{bad}")

# core_members 里点名的人,补完后应当都能对上号
wanted = set()
for f in glob.glob("data/entities/factions/*.yaml"):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    wanted |= set(d.get("core_members") or [])
new_names = {p["name"] for p in PEOPLE}
still = {w for w in wanted if w not in byname and w not in new_names}
# 带括号注释的名字(「朱温(降唐前)」)不是新人,留给下一步迁移时剥注释
still = {w for w in still if "(" not in w and "（" not in w}
if still: sys.exit(f"✗ 仍有 core_members 无人对应,本脚本没补全:{sorted(still)}")

n = 0
for p in PEOPLE:
    path = f"data/entities/persons/{p['id'].split('_',1)[1]}.yaml"
    if pathlib.Path(path).exists(): sys.exit(f"✗ 文件已存在:{path}")
    yaml.safe_dump(p, open(path, "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False, width=200)
    n += 1
print(f"新建 {n} 个人物;core_members 点名者已全部有实体对应(带括号注释者除外)")
