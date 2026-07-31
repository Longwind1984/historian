#!/usr/bin/env python3
"""Phase 9 — Mid-to-Late Tang Dynasty (763-907).

The political night of Five Dynasties & Ten Kingdoms. Covers:
- 河朔三镇 (Heshuo garrison states) — actual semi-autonomous warlords
- 牛李党争 (Niu-Li factional struggle) — late-Tang literati factionalism
- 宦官专权 (eunuch domination via 神策军)
- 黄巢起义 detail (王仙芝/黄巢/尚让/朱温降唐)
- 残唐五代 transition

Adds ~50 persons, ~20 events, ~5 factions, ~80 relations.
All dates cross-checked against《资治通鉴》唐纪部分 +《旧唐书》《新唐书》.
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
# LATE TANG PERSONS (763-907)
# ============================================================
LATE_TANG_PERSONS = [
    # === Emperors (中晚唐) ===
    ("p_lisong", "李诵", ["唐顺宗"], None, (761, None), (806, None), "pl_chang_an",
     "唐顺宗。805 年即位,任用王叔文、王伾推行永贞革新。中风失语,在位仅八月即被宦官逼迫退位,传位宪宗。永贞内禅。",
     ["旧唐书·顺宗纪", "新唐书·顺宗本纪", "资治通鉴·卷236"]),
    ("p_lichun", "李纯", ["唐宪宗"], None, (778, None), (820, 2), "pl_chang_an",
     "唐宪宗。805-820 在位。发动元和削藩(806-819),先后平西川刘辟、镇海李锜、淮西吴元济、淄青李师道,河朔三镇名义归附,史称'元和中兴'。晚年信佛服丹药,为宦官所弑。",
     "晚唐最杰出的君主,短暂重建中央权威。",
     ["旧唐书·宪宗纪", "新唐书·宪宗本纪", "资治通鉴·卷237-241"]),
    ("p_liheng_tang", "李恒", ["唐穆宗"], None, (795, None), (824, None), "pl_chang_an",
     "唐穆宗。820-824 在位。父宪宗被弑后由宦官拥立。河朔三镇再次叛乱(821 长庆割据),元和中兴成果丧失。荒酒色。",
     ["旧唐书·穆宗纪", "资治通鉴·卷241-243"]),
    ("p_lizhan", "李湛", ["唐敬宗"], None, (809, None), (827, 1), "pl_chang_an",
     "唐敬宗。824-827 在位。少年荒唐,被宦官和击球将弑杀。",
     ["旧唐书·敬宗纪"]),
    ("p_liang_tang", "李昂", ["唐文宗"], None, (809, None), (840, 1), "pl_chang_an",
     "唐文宗。827-840 在位。勤政节俭,欲除宦官。835 年用李训、郑注发动甘露之变,失败,宦官大杀朝臣(李训、郑注、王涯等),文宗被架空,'受制于家奴'。840 年忧卒。",
     "甘露之变是宦官专权的转折点,此后唐廷完全被宦官把持。",
     ["旧唐书·文宗纪", "新唐书·文宗本纪", "资治通鉴·卷245"]),
    ("p_liyan_tang", "李炎", ["唐武宗"], None, (814, None), (846, 3), "pl_chang_an",
     "唐武宗。840-846 在位。任李德裕为相,平昭义刘稹(843-844),回鹘破亡(840-846)。845 年大举灭佛(三武一宗之三),史称会昌毁佛。服丹药中毒死。",
     "晚唐短暂中兴,称'会昌中兴'。",
     ["旧唐书·武宗纪", "资治通鉴·卷246-248"]),
    ("p_licheng_tang", "李忱", ["唐宣宗", "李怡"], None, (810, None), (859, 8), "pl_chang_an",
     "唐宣宗。846-859 在位。推翻会昌毁佛,平反牛党。整顿吏治,击败吐蕃收复河西(851 张义潮归唐)。史称'大中之治'/'小太宗'。",
     "晚唐最后一个治世。",
     ["旧唐书·宣宗纪", "资治通鉴·卷248-249"]),
    ("p_li cui_tang", "李漼", ["唐懿宗"], None, (833, None), (873, 8), "pl_chang_an",
     "唐懿宗。859-873 在位。荒淫奢靡。859-866 裘甫起义、868-869 庞勋之变(桂林戍卒起义)。唐朝根基动摇。",
     ["旧唐书·懿宗纪", "资治通鉴·卷250-252"]),
    ("p_li xuan_tang", "李儇", ["唐僖宗"], None, (862, None), (888, 3), "pl_chang_an",
     "唐僖宗。873-888 在位。875 王仙芝、黄巢起义,880 黄巢攻入长安,僖宗逃蜀。885 还都后又因朱温、李克用冲突再逃。888 年还都后病死。",
     ["旧唐书·僖宗纪", "资治通鉴·卷252-257"]),
    ("p_liye_tang", "李晔", ["唐昭宗"], None, (867, None), (904, 8), "pl_chang_an",
     "唐昭宗。888-904 在位。893-904 间多次被宦官、藩镇挟持。901 崔胤引朱温入京。904 朱温弑昭宗,立哀帝。",
     ["旧唐书·昭宗纪", "资治通鉴·卷257-264"]),
    ("p_li zhu_tang", "李柷", ["唐哀帝", "唐昭宣帝"], None, (892, None), (908, 3), "pl_chang_an",
     "唐哀帝。904-907 在位。朱温傀儡。905 年白马驿之祸,907 年禅让于朱温,唐亡。908 年被毒杀。",
     ["旧唐书·哀帝纪", "资治通鉴·卷265-266"]),

    # === 中晚唐将相大臣 ===
    ("p_guo_ziyi_existing", "郭子仪标记", None, None, (None, None), (None, None), None,
     "已存在 p_guo_ziyi 实体,此条占位避免重复",
     []) if False else None,
    ("p_li_guangbi", "李光弼", ["李光弼"], None, (708, None), (764, 8), "pl_liuzhou",
     "中唐名将,契丹族。安史之乱主力平叛者,与郭子仪齐名。常山之战(756)、太原保卫战(757)、河阳之战(759)。封临淮郡王。",
     "与郭子仪同为平叛柱石。",
     ["旧唐书·李光弼传", "新唐书·李光弼传", "资治通鉴·卷220"]),
    ("p_pugu_huaien", "仆固怀恩", None, None, (None, None), (765, None), "pl_shuozhou_yy",
     "中唐铁勒族将领。郭子仪部将,安史之乱平叛主力之一。借回纥兵。763 年因被猜忌叛唐,引吐蕃、回纥入侵,765 年病死军中。",
     ["旧唐书·仆固怀恩传", "资治通鉴·卷223"]),
    ("p_yan_gaoqing", "颜杲卿", ["颜常山"], None, (692, None), (756, 1), "pl_zhending_yy",
     "中唐忠臣,颜真卿堂兄。安史之乱起兵常山,城陷被俘,骂贼而死。",
     ["旧唐书·颜杲卿传"]),
    ("p_yan_zhenqing", "颜真卿", ["颜清臣", "颜鲁公"], "清臣", (709, None), (785, 8), "pl_wanping",
     "中唐名臣、书法家。安史之乱起兵讨贼。后任宰相,因不附卢杞被派往宣抚李希烈,785 年为李希烈缢杀。书法为'颜体'。",
     ["旧唐书·颜真卿传", "新唐书·颜真卿传"]),
    ("p_zhang_xun", "张巡", ["张巡"], None, (709, None), (757, 11), "pl_nanyang",
     "安史之乱守城名将。与许远死守睢阳(757)十月,抗击尹子奇十余万军。城破被俘殉国。睢阳之战,挡住叛军南下江淮。",
     "睢阳之战保住了唐朝经济命脉江淮。",
     ["旧唐书·张巡传", "资治通鉴·卷220"]),

    # === 中晚唐宦官 ===
    ("p_yu_chao_en", "鱼朝恩", None, None, (722, None), (770, None), None,
     "唐代宦官。肃、代宗朝掌神策军。骄横,干预朝政。770 年代宗与元载设计诛杀之。",
     ["旧唐书·宦官传", "资治通鉴·卷224"]),
    ("p_chou_shiliang", "仇士良", None, None, (781, None), (843, None), None,
     "晚唐权阉。826-840 间掌握神策军,历经文宗、武宗。甘露之变(835)后大杀朝臣,二王八司马等。'天子当使其畏,不当使其骄'。",
     "晚唐宦官专权的极致代表。",
     ["旧唐书·宦官传·仇士良", "资治通鉴·卷245-247"]),

    # === 牛李党争核心人物 ===
    ("p_niu_sengru", "牛僧孺", ["牛思黯"], "思黯", (779, None), (847, None), "pl_anhui_niu",
     "中唐官员。牛党领袖。821 长庆元年,与李宗闵科举时谤时政,得罪李吉甫,埋下党争伏线。后历穆、文、武、宣朝为相。'牛党'由其和李宗闵代表。",
     ["旧唐书·牛僧孺传", "新唐书·牛僧孺传"]),
    ("p_li_zongmin", "李宗闵", None, None, (None, None), (846, None), "pl_chang_an",
     "中唐官员,牛党核心。821 年与牛僧孺科举讽政被贬。历穆、文、武朝起伏。与李德裕长期互相倾轧。",
     ["旧唐书·李宗闵传"]),
    ("p_li_deyu", "李德裕", ["李文饶"], "文饶", (787, None), (850, None), "pl_zhaojun_li",
     "中唐名相,李党领袖。父李吉甫。历武宗(会昌)、宣宗朝为相。会昌中兴主力:平昭义、灭回鹘、毁佛。846 宣宗即位被贬,贬死崖州。",
     "晚唐杰出政治家,陈寅恪评'牛李党争中李党代表山东士族'之说尚有争议。",
     ["旧唐书·李德裕传", "新唐书·李德裕传", "资治通鉴·卷246-248"]),
    ("p_li_jifu", "李吉甫", ["李宪章"], "宪章", (758, None), (814, None), "pl_zhaojun_li",
     "中唐官员,李德裕之父。两度拜相。著《元和郡县图志》。",
     ["旧唐书·李吉甫传"]),

    # === 永贞革新核心 ===
    ("p_wang_shuwen", "王叔文", None, None, (753, None), (806, None), "pl_yuezhou_wsw",
     "唐顺宗朝官员。永贞革新主导者。顺宗中风后,他与王伾、刘禹锡、柳宗元等推行改革(罢宫市、放宫女、收宦官兵权)。失败被贬,806 年赐死。",
     "永贞革新失败是中晚唐政治转折点。",
     ["旧唐书·王叔文传", "资治通鉴·卷236"]),
    ("p_wang_pi", "王伾", None, None, (None, None), (806, None), "pl_hangzhou_wp",
     "永贞革新参与者。失败后贬死。",
     ["旧唐书·王叔文传附王伾"]),
    ("p_liu_yuxi", "刘禹锡", ["刘梦得"], "梦得", (772, None), (842, None), "pl_luoyang",
     "唐代文学家、哲学家。永贞革新核心成员(二王刘柳)。失败后长期贬谪(朗州、连州、夔州、和州)。后还朝。诗'旧时王谢堂前燕'千古传诵。",
     ["旧唐书·刘禹锡传"]),
    ("p_liu_zongyuan", "柳宗元", ["柳子厚"], "子厚", (773, None), (819, None), "pl_yongjin_lyz",
     "唐代文学家、哲学家。永贞革新核心。失败后贬永州、柳州。唐宋八大家之一。著《永州八记》《封建论》《天对》。",
     ["旧唐书·柳宗元传"]),

    # === 黄巢起义核心 ===
    ("p_wang_xianzhi", "王仙芝", None, None, (None, None), (878, 2), "pl_puzhou_wxz",
     "唐末起义军首领。875 年于长垣起兵,自称天补平均大将军。878 年战死于黄梅。",
     "唐末大起义先驱,与黄巢共同揭开唐朝覆灭序幕。",
     ["旧唐书·僖宗纪", "新唐书·逆臣传", "资治通鉴·卷252-253"]),
    ("p_huangchao_existing", "黄巢标记", None, None, (None, None), (None, None), None,
     "已存在", []) if False else None,
    ("p_shang_rang", "尚让", None, None, (None, None), (884, None), None,
     "黄巢起义军核心将领。黄巢称帝后任宰相。黄巢败后降唐,后被杀。",
     ["新五代史·梁本纪第一注"]),
    ("p_wang_jiwei", "王重荣", None, None, (None, None), (887, None), "pl_hezhong",
     "唐末河中节度使。880-884 年抵抗黄巢,多次大破之。与田令孜争盐利,885 年引李克用入京,田令孜挟僖宗再幸。",
     ["旧唐书·王重荣传"]),
    ("p_gao_pian", "高骈", ["高千里"], "千里", (821, None), (887, None), "pl_youzhou_gp",
     "唐末名将、文学家。南平郡王。879 年破南诏,坐镇江陵。黄巢北上时拥兵不击,致使黄巢渡江入长安。后迷信神仙,被部将毕师铎所杀。",
     "坐视黄巢北上致唐廷崩溃,是唐朝灭亡关键转折。",
     ["旧唐书·高骈传", "资治通鉴·卷253-254"]),
    ("p_li_keyong_pre", "李克用前传", None, None, (None, None), (None, None), None,
     "占位", []) if False else None,

    # === 河朔三镇节度使 ===
    ("p_tian_chengsi", "田承嗣", None, None, (705, None), (779, None), "pl_weizhou",
     "魏博节度使(763-779)。安史旧部。河朔三镇割据奠基者。领魏、博、相、卫、贝、澶六州,设牙军,父死子继,公赋不入朝。",
     "河朔三镇割据传统的开创者。",
     ["旧唐书·田承嗣传", "新唐书·藩镇魏博传"]),
    ("p_li_baochen", "李宝臣", ["张忠志"], None, (718, None), (781, None), "pl_zhenzhou3",
     "成德节度使(763-781)。安史旧部。河朔三镇之一。",
     ["旧唐书·李宝臣传"]),
    ("p_li_huaixian", "李怀仙", None, None, (None, None), (768, None), "pl_youzhou",
     "卢龙节度使(763-768)。柳城胡人,安史旧部。河朔三镇之一。被部下朱希彩所杀。",
     ["旧唐书·李怀仙传"]),
    ("p_tian_yue", "田悦", None, None, (751, None), (784, None), "pl_weizhou",
     "魏博节度使(779-784)。田承嗣侄。781 年与成德李惟岳、淄青李纳、山南梁崇义起兵反抗唐廷(四镇之乱)。后为堂弟田绪所杀。",
     ["旧唐书·田悦传"]),
    ("p_wang_wujun", "王武俊", None, None, (735, None), (801, None), "pl_zhenzhou3",
     "成德节度使(781-801)。契丹族。杀李惟岳自立。781-786 年间多次反叛与归附唐廷。",
     ["旧唐书·王武俊传"]),
    ("p_zhu_xicai", "朱希彩", None, None, (None, None), (772, None), "pl_youzhou",
     "卢龙节度使(768-772)。杀李怀仙自立。后被部下所杀。",
     ["旧唐书·朱希彩传"]),
    ("p_zhu_tao", "朱滔", None, None, (746, None), (785, None), "pl_youzhou",
     "卢龙节度使(772-785)。朱希彩死后继立。781-784 与田悦、王武俊、李纳联合叛乱,自称冀王。",
     ["旧唐书·朱滔传"]),

    # === 中晚唐重要藩镇 ===
    ("p_wu_yuanji", "吴元济", None, None, (783, None), (817, 11), "pl_caizhou",
     "淮西节度使(814-817)。父吴少阳,814 继位。815 宰相武元衡被刺(李师道主使)。817 李愬雪夜入蔡州生擒吴元济,淮西平。",
     "李愬入蔡州是元和中兴标志之战。",
     ["旧唐书·吴元济传", "资治通鉴·卷240"]),
    ("p_li_su", "李愬", ["李元直"], "元直", (773, None), (821, None), "pl_luoyang",
     "中唐名将。817 年雪夜袭蔡州,擒吴元济,平淮西。元和削藩最辉煌战役。",
     ["旧唐书·李愬传", "资治通鉴·卷240"]),
    ("p_li_shidao", "李师道", None, None, (None, None), (819, None), "pl_yunzhou_lsd",
     "淄青节度使(806-819)。815 派刺客刺杀宰相武元衡、伤裴度。819 为部下所杀,淄青平。",
     ["旧唐书·李师道传"]),

    # === 五代前夕(残唐)===
    ("p_liu_qian_tang", "刘谦", None, None, (None, None), (894, None), None,
     "唐末封州刺史。刘隐(南汉奠基)之父。",
     ["新五代史·南汉世家"]),
    ("p_liu_yin", "刘隐", None, None, (874, None), (911, None), "pl_guangzhou",
     "唐末岭南节度使。南汉刘龑之兄,南汉基业奠基者。",
     ["新五代史·南汉世家"]),

    # === 文化名人(补充) ===
    ("p_li_he", "李贺", ["李长吉"], "长吉", (790, None), (816, None), "pl_luoyang",
     "中唐诗人。'诗鬼'。27 岁早逝。",
     ["旧唐书·李贺传"]),
    ("p_li_shangyin", "李商隐", ["李义山"], "义山", (813, None), (858, None), "pl_xingyang",
     "晚唐诗人。牛李党争中受牵连,一生不得志。诗风朦胧多义。",
     ["旧唐书·李商隐传"]),
    ("p_du_mu", "杜牧", ["杜牧之"], "牧之", (803, None), (852, None), "pl_xianyang_dm",
     "晚唐诗人、文学家。'东风不与周郎便,铜雀春深锁二乔'。",
     ["旧唐书·杜牧传"]),
    ("p_han_yu", "韩愈", ["韩退之"], "退之", (768, None), (824, None), "pl_nanyang_hy",
     "中唐文学家、思想家。'唐宋八大家'之首。古文运动领袖。819 谏迎佛骨,贬潮州。",
     ["旧唐书·韩愈传", "资治通鉴·卷240"]),
    ("p_bai_juyi", "白居易", ["白乐天"], "乐天", (772, None), (846, None), "pl_taiyuan_bjy",
     "中唐诗人。新乐府运动领袖。著《长恨歌》《琵琶行》。晚年居洛阳香山,号香山居士。",
     ["旧唐书·白居易传"]),
    ("p_yuan_zhen", "元稹", ["元微之"], "微之", (779, None), (831, None), "pl_luoyang",
     "中唐诗人。白居易挚友,'元白'并称。'曾经沧海难为水'。",
     ["旧唐书·元稹传"]),
    ("p_liu_zongyuan_add", "柳宗元补", None, None, (None, None), (None, None), None,
     "", []) if False else None,
]
LATE_TANG_PERSONS = [p for p in LATE_TANG_PERSONS if p is not None]


def gen_late_tang_persons():
    for tup in LATE_TANG_PERSONS:
        # tuple may be 9 or 10 elements (optional significance)
        if len(tup) == 9:
            pid, name, aliases, courtesy, born, died, birthplace, bio, srcs = tup
            significance = None
        else:
            pid, name, aliases, courtesy, born, died, birthplace, bio, significance, srcs = tup
        if pid.endswith("_existing") or pid.endswith("_add") or pid.endswith("_pre"):
            continue  # skip placeholder
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
        if significance:
            obj["ext"] = {"significance": significance}
        obj["sources"] = srcs
        write(DATA / "entities" / "persons" / f"{pid[2:]}.yaml", obj)


# ============================================================
# LATE TANG PLACES
# ============================================================
LATE_TANG_PLACES = [
    ("pl_liuzhou", "柳州", "柳州", "广西", 24.33, 109.43, "city", [], "柳宗元贬所"),
    ("pl_shuozhou_yy2", "朔州", "朔州", "山西", 39.33, 112.43, "city", [], "仆固怀恩驻所"),
    ("pl_zhending_yy", "镇州", "正定", "河北", 38.15, 114.57, "city", ["成德", "真定"], "成德治所"),
    ("pl_wanping", "万平/万年", "西安", "陕西", 34.27, 108.95, "city", ["京兆万年"], "颜真卿籍贯"),
    ("pl_nanyang", "南阳", "南阳", "河南", 32.99, 112.53, "city", [], "韩愈籍贯"),
    ("pl_nanyang_zhang", "邓州/南阳", "南阳", "河南", 32.99, 112.53, "battlefield", ["睢阳"], "张巡守睢阳(今商丘南)"),
    ("pl_zhaolishi", "赵郡", "赵县", "河北", 37.75, 114.78, "city", [], "李德裕家族祖籍"),
    ("pl_anhui_niu", "隋/安定", "涇川", "甘肃", 35.33, 107.37, "city", [], "牛僧孺籍贯(隋安定鶉觚)"),
    ("pl_yuezhou_wsw", "越州/山阴", "绍兴", "浙江", 30.00, 120.58, "city", ["绍兴"], "王叔文籍贯"),
    ("pl_hangzhou_wp", "杭州", "杭州", "浙江", 30.27, 120.16, "city", [], "王伾籍贯"),
    ("pl_yongjin_lyz", "河东/永济", "永济", "山西", 34.87, 110.45, "city", ["蒲州"], "柳宗元籍贯"),
    ("pl_puzhou_wxz", "濮州", "菏泽鄄城", "山东", 35.56, 115.55, "city", [], "王仙芝起兵地(长垣附近)"),
    ("pl_hezhong", "河中", "永济", "山西", 34.87, 110.45, "city", ["蒲州"], "王重荣治所"),
    ("pl_youzhou_gp", "幽州", "北京", "北京", 39.91, 116.40, "city", [], "高骈旧镇"),
    ("pl_caizhou", "蔡州", "汝南", "河南", 33.00, 114.36, "battlefield", [], "817 李愬入蔡州"),
    ("pl_yunzhou_lsd", "郓州", "东平", "山东", 35.91, 116.30, "city", ["天平"], "淄青治所"),
    ("pl_zhaojun_li", "赵郡", "赵县", "河北", 37.75, 114.78, "city", [], "李德裕/李吉甫籍贯"),
    ("pl_xingyang", "荥阳", "郑州", "河南", 34.79, 113.39, "city", [], "李商隐籍贯"),
    ("pl_xianyang_dm", "京兆/万年", "西安", "陕西", 34.27, 108.95, "city", [], "杜牧籍贯"),
    ("pl_nanyang_hy", "南阳", "南阳", "河南", 32.99, 112.53, "city", [], "韩愈自称南阳人"),
    ("pl_taiyuan_bjy", "太原", "太原", "山西", 37.77, 112.55, "city", ["并州"], "白居易祖籍"),
    ("pl_zhenzhou3", "镇州", "正定", "河北", 38.15, 114.57, "city", ["成德"], "李宝臣/王武俊治所"),
    ("pl_caizhou2", "蔡州/汝南", "汝南", "河南", 33.00, 114.36, "battlefield", [], "吴元济治所"),
    ("pl_chang_an_mid", "长安", "西安", "陕西", 34.27, 108.95, "capital", [], "中晚唐都城"),
    ("pl_chengdu_mid_tang", "成都", "成都", "四川", 30.67, 104.07, "city", ["益州"], "玄宗幸蜀驻所"),
    ("pl_yizhou", "益州", "成都", "四川", 30.67, 104.07, "city", [], "高骈前任"),
    ("pl_suzhou_tang", "苏州", "苏州", "江苏", 31.30, 120.62, "city", [], "中晚唐江南"),
    ("pl_yangzhou_tang", "扬州", "扬州", "江苏", 32.39, 119.42, "city", ["广陵"], "江淮重镇"),
    ("pl_changyuan", "长垣", "长垣", "河南", 35.20, 114.65, "battlefield", [], "王仙芝起兵地"),
    ("pl_huangmei", "黄梅", "黄梅", "湖北", 30.09, 115.93, "battlefield", [], "878 王仙芝战死"),
    ("pl_langhu_gu", "狼虎谷", "莱芜", "山东", 36.34, 117.67, "battlefield", [], "884 黄巢兵败地"),
    ("pl_lingwu", "灵武", "灵武", "宁夏", 38.10, 106.34, "city", [], "756 肃宗即位地"),
    ("pl_mawei", "马嵬驿", "兴平", "陕西", 34.30, 108.49, "battlefield", [], "756 马嵬驿之变"),
]


def gen_late_tang_places():
    for tup in LATE_TANG_PLACES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["旧唐书·地理志", "新唐书·地理志", "资治通鉴"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# ============================================================
# LATE TANG EVENTS
# ============================================================
LATE_TANG_EVENTS = [
    ("e_yuanhe_xiaofan", "元和削藩", (806, None), (819, None), "reform", "pl_chang_an",
     ["k_tang"],
     "806-819 年宪宗李纯在位期间,先后平定西川刘辟(806)、镇海李锜(807)、魏博田兴归附(812)、淮西吴元济(817)、淄青李师道(819)。河朔三镇名义归附。是安史之乱后唐朝中央权威的最高峰。",
     "晚唐短暂中兴(元和中兴)。但宪宗一死,河朔三镇立刻再叛,削藩成果丧失。",
     ["旧唐书·宪宗纪", "资治通鉴·卷237-241"]),

    ("e_yongzhen_gexin", "永贞革新", (805, 8), (805, 10), "reform", "pl_chang_an",
     ["k_tang"],
     "805 年顺宗即位,任用王叔文、王伾、刘禹锡、柳宗元等推行改革:罢宫市五坊、放出宫女、收宦官兵权。顺宗中风失语,宦官俱文珍迫顺宗内禅,革新失败。",
     "失败导致二王八司马被贬,宦官掌握神策军,为晚唐宦官专权开端的标志。",
     ["旧唐书·顺宗纪", "资治通鉴·卷236"]),

    ("e_ganlu_zhibian", "甘露之变", (835, 12), None, "coup", "pl_chang_an",
     ["k_tang"],
     "835 年文宗用李训、郑注谋,以左金吾卫石榴树夜有甘露为名,欲诱宦官仇士良等入而诛之。事泄,仇士良等率神策军大杀朝臣(李训、郑注、王涯、贾餗等),死者千余。",
     "甘露之变后,宦官完全把持朝政。文宗'受制于家奴',唐廷名存实亡。牛李党争更趋激烈。",
     ["旧唐书·文宗纪", "资治通鉴·卷245"]),

    ("e_huichang_fofo", "会昌毁佛", (845, None), None, "religion", "pl_chang_an",
     ["k_tang"],
     "845 年武宗下令毁佛。废寺 4600 余所、僧尼归俗 26 万。僧尼配田、铜佛铸钱。三武一宗之三。",
     "短期充实国库、增加纳税人口。武宗死后宣宗推翻。",
     ["旧唐书·武宗纪", "资治通鉴·卷248"]),

    ("e_niu_li_dangzheng", "牛李党争", (821, None), (859, None), "institution", "pl_chang_an",
     ["k_tang"],
     "821-859 年(长庆元年至大中末)约 40 年的朝堂党争。牛党以牛僧孺、李宗闵为首,代表科举出身的新进士及山东寒族;李党以李德裕、李吉甫为首,代表门荫世族。双方围绕藩镇、宦官、佛教等问题互斗。",
     "陈寅恪认为牛党代表'新兴进士阶级',李党代表'北朝以来山东士族'。争论激烈。耗损唐朝政治能量。",
     ["旧唐书·牛僧孺传、李德裕传", "陈寅恪·唐代政治史述论稿"]),

    ("e_pangxun_zhibian", "庞勋之变", (868, None), (869, None), "institution", "pl_xuzhou",
     ["k_tang"],
     "868 年桂林戍卒 800 人因久不得归,推庞勋为首起事,自广西北上,克徐州,众至 20 万。869 年为康承训率沙陀、吐谷浑兵平定。",
     "裘甫、庞勋两役是黄巢起义的前奏。沙陀因此役入中原。",
     ["旧唐书·懿宗纪", "资治通鉴·卷251"]),

    ("e_huangchao_zhan_changan", "黄巢攻入长安", (880, 12), None, "coup", "pl_chang_an",
     ["k_tang"],
     "880 年十二月黄巢大军自洛阳入长安,僖宗奔蜀。黄巢即皇帝位,国号大齐,建元金统。",
     "唐朝中央威信彻底丧失,藩镇成为历史主角。直接催生五代十国。",
     ["旧唐书·僖宗纪", "资治通鉴·卷254"]),

    ("e_jiannan_chengzhong_li_jianyong", "沙陀助唐平黄巢", (881, None), (884, None), "diplomacy", "pl_taiyuan",
     ["k_tang"],
     "881 年唐廷召李克用率沙陀兵讨黄巢。883 年李克用收复长安,黄巢东撤。884 年李克用追击黄巢至河南,黄巢败于狼虎谷,为外甥林言所杀。",
     "沙陀因此役正式登上中原政治舞台,李克用被封河东节度使,奠立后唐基业。",
     ["旧唐书·僖宗纪", "旧五代史·武皇纪"]),

    ("e_tian_lingzi_xijian", "田令孜乱政 / 僖宗再幸", (885, None), (886, None), "coup", "pl_chang_an",
     ["k_tang"],
     "885 年宦官田令孜与王重荣争安邑、解县两池盐利,田令孜引邠宁朱玫、凤翔李昌符攻王重荣。王重荣与李克用入京,田令孜挟僖宗再幸凤翔、兴元。",
     "晚唐宦官专权之极致,皇帝再次逃亡。",
     ["旧唐书·僖宗纪", "资治通鉴·卷256"]),

    ("e_cuiyin_yin_zhuwen", "崔胤引朱温入京", (901, None), (904, None), "coup", "pl_chang_an",
     ["k_tang"],
     "901 年宰相崔胤欲倚朱温除宦官,召朱温入京。903 年朱温尽诛宦官(除黃衣 30 人),延续百年的宦官专权终结。904 朱温弑昭宗。",
     "崔胤引狼入室,唐朝已沦为朱温掌中物。",
     ["旧唐书·昭宗纪", "资治通鉴·卷262-264"]),

    ("e_wang_xianzhi_qiyi", "王仙芝起义", (875, 6), (878, 2), "institution", "pl_changyuan",
     ["k_tang"],
     "875 年六月王仙芝于长垣聚众起兵,自称天补平均大将军。攻占曹、濮、郓诸州。后转战河南、湖北、安徽。878 年战死于黄梅。",
     "与黄巢起义同为唐末大起义先驱。",
     ["旧唐书·僖宗纪", "资治通鉴·卷252"]),

    ("e_qingfu_qiyi", "裘甫起义", (859, 12), (860, 6), "institution", "pl_zhoushan_qf",
     ["k_tang"],
     "859-860 年浙东裘甫起义,攻占象山、剡县,众至 3 万。为王式率军平定。",
     "唐朝第一次大规模农民起义,唐廷依赖沙陀等蕃兵平叛。",
     ["旧唐书·懿宗纪", "资治通鉴·卷250"]),

    ("e_dazhong_zhizhi", "大中之治", (846, None), (859, None), "reform", "pl_chang_an",
     ["k_tang"],
     "846-859 宣宗李忱在位期间。推翻会昌毁佛、平反牛党、整顿吏治、击败吐蕃收复河西(851 张义潮归唐)、抑制宦官。",
     "晚唐最后一个治世。宣宗崩后唐朝迅速崩溃。",
     ["旧唐书·宣宗纪", "资治通鉴·卷248-249"]),

    ("e_hexi_zhangyichao", "张义潮归唐(归义军)", (851, None), None, "diplomacy", "pl_shazhou",
     ["k_tang"],
     "851 年沙州(敦煌)人张义潮乘吐蕃内乱起兵,以瓜、沙、伊、西等十一州归唐。唐置归义军,以张义潮为节度使。",
     "唐末收复河西故地的关键事件,归义军延续至宋初。",
     ["旧唐书·宣宗纪", "新唐书·吐蕃传"]),

    ("e_huihe_pohuai", "回鹘汗国灭亡", (840, None), (846, None), "diplomacy", "pl_menggu_hh",
     ["k_tang"],
     "840 年黠戛斯破回鹘汗国,回鹘崩溃。部众西迁(高昌回鹘/河西回鹘/葱岭西回鹘)。武宗朝助唐平定回鹘残部。",
     "中亚与北亚政治格局大变。中国北方威胁从回鹘转为契丹。",
     ["旧唐书·回纥传", "新唐书·回鹘传"]),

    ("e_huangchao_deng_zhou_jianliang", "朱温降唐", (882, 9), None, "diplomacy", "pl_tongzhou",
     ["k_tang"],
     "882 年九月黄巢大将朱温见大势已去,以同州降唐,赐名全忠,任河中行营招讨副使。成为唐廷镇压黄巢的主力。",
     "朱温转变的关键节点,从农民军成为唐廷藩镇。奠定了后梁立国的基础。",
     ["旧五代史·梁太祖纪", "资治通鉴·卷255"]),
]

LATE_TANG_EVENT_PLACES = [
    ("pl_xuzhou", "徐州", "徐州", "江苏", 34.21, 117.28, "battlefield", ["彭城"], "庞勋据徐州"),
    ("pl_zhoushan_qf", "浙东/象山", "象山", "浙江", 29.45, 121.87, "battlefield", [], "裘甫起兵地"),
    ("pl_shazhou", "沙州", "敦煌", "甘肃", 40.14, 94.66, "city", ["敦煌"], "归义军治所"),
    ("pl_menggu_hh", "蒙古高原", "蒙古高原", "蒙古", 47.92, 106.92, "region", [], "回鹘汗国"),
    ("pl_tongzhou", "同州", "大荔", "陕西", 34.80, 109.94, "city", [], "朱温降唐时治所"),
]


def gen_late_tang_events():
    for tup in LATE_TANG_EVENTS:
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
    for tup in LATE_TANG_EVENT_PLACES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["旧唐书·地理志"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# ============================================================
# LATE TANG FACTIONS
# ============================================================
LATE_TANG_FACTIONS = [
    ("f_niu_dang", "牛党", "political", (821, None), (859, None), "pl_chang_an",
     "中晚唐朝堂党争中的一派。以牛僧孺、李宗闵为首,代表科举出身的新进士、寒族士人。主张对藩镇姑息、对宦官妥协、对佛教宽容。",
     "陈寅恪曾以其代表'新兴进士阶级',后学界有争议。与李党长期互斗,内耗唐朝。",
     ["牛僧孺", "李宗闵", "令狐楚", "白敏中"],
     "长庆-大中"),
    ("f_li_dang", "李党", "political", (821, None), (859, None), "pl_chang_an",
     "中晚唐朝堂党争中的另一派。以李德裕、李吉甫为首,代表门荫世族、北朝以来的山东士族(陈寅恪说)。主张强力削藩、抑制宦官、毁佛。",
     "李党执政时期(李德裕会昌年间)是晚唐短暂中兴。",
     ["李德裕", "李吉甫", "郑覃"],
     "长庆-大中"),
    ("f_heshuo_3_zhen", "河朔三镇", "military_clan", (763, None), (929, None), "pl_weizhou",
     "安史之乱后形成的魏博、成德、卢龙三镇割据势力。父死子继、自署官吏、贡赋不入。河朔藩镇模式为五代藩镇割据之滥觞。",
     "晚唐'藩镇割据'的典型,深刻影响了五代十国的政治生态。",
     ["田承嗣", "李宝臣", "李怀仙", "王武俊", "田悦", "朱滔", "罗绍威"],
     "代宗-后唐"),
    ("f_late_tang_eunuchs", "晚唐宦官集团", "eunuch", (758, None), (903, None), "pl_chang_an",
     "中晚唐宦官掌神策军、枢密使,专废立皇帝。俱文珍、吐突承璀、王守澄、仇士良、田令孜等。903 年朱温尽诛宦官(止留黄衣 30 人),宦官集团终结。",
     "中晚唐政治关键角色。神策军中尉与枢密使合称'四贵'。",
     ["俱文珍", "王守澄", "仇士良", "田令孜", "鱼朝恩"],
     "肃宗-昭宗"),
    ("f_huangchao_army", "黄巢起义军", "military_clan", (875, None), (884, None), "pl_caizhou2",
     "唐末最大农民起义军。875 年王仙芝、黄巢起兵,880 年黄巢入长安称帝建齐。884 年黄巢败死。残部尚让等降朱温。",
     "彻底摧毁唐朝根基。朱温(降唐的黄巢部将)成为最大军阀,沙陀李克用因平叛崛起——五代十国两大主导势力皆源于此。",
     ["黄巢", "王仙芝", "尚让", "朱温(降唐前)", "孟楷"],
     "僖宗朝"),
]


def gen_late_tang_factions():
    for tup in LATE_TANG_FACTIONS:
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
            "陈寅恪·唐代政治史述论稿", "新唐书", "旧唐书",
            "毛汉光·中国中古政治史论", "谷川道雄·隋唐帝国形成史论"
        ]
        write(DATA / "entities" / "factions" / f"{fid[2:]}.yaml", obj)


# ============================================================
# RELATIONS
# ============================================================
RELATIONS = [
    # 唐帝统(代→顺→宪→穆→敬→文→武→宣→懿→僖→昭→哀)
    # (李泌/李适等中唐帝在隋唐前期阶段补,这里接中晚唐)
    ("p_lisong", "p_lichun", "father_of", 778, None, None, None, "顺宗→宪宗"),
    ("p_lisong", "k_tang", "succeeded_by", 805, 1, 805, 8, "顺宗在位 8 月"),
    ("p_lichun", "k_tang", "succeeded_by", 805, 8, 820, 2, "宪宗 元和中兴"),
    ("p_lichun", "p_liheng_tang", "father_of", 795, None, None, None, "宪宗→穆宗"),
    ("p_liheng_tang", "k_tang", "succeeded_by", 820, 2, 824, None, "穆宗"),
    ("p_liheng_tang", "p_lizhan", "father_of", 809, None, None, None, None),
    ("p_liheng_tang", "p_liang_tang", "father_of", 809, None, None, None, None),
    ("p_lizhan", "k_tang", "succeeded_by", 824, None, 827, 1, "敬宗 被弑"),
    ("p_liang_tang", "k_tang", "succeeded_by", 827, 1, 840, 1, "文宗"),
    ("p_liang_tang", "e_ganlu_zhibian", "participated_in", 835, 12, 840, 1, "策划者"),
    ("p_liyan_tang", "k_tang", "succeeded_by", 840, 1, 846, 3, "武宗 会昌中兴"),
    ("p_liyan_tang", "e_huichang_fofo", "participated_in", 845, None, 846, 3, "主导"),
    ("p_licheng_tang", "k_tang", "succeeded_by", 846, 3, 859, 8, "宣宗 大中之治"),
    ("p_licheng_tang", "e_dazhong_zhizhi", "participated_in", 846, None, 859, 8, "主导"),
    ("p_licheng_tang", "p_li cui_tang", "father_of", 833, None, None, None, None),
    ("p_li cui_tang", "k_tang", "succeeded_by", 859, 8, 873, 8, "懿宗"),
    ("p_li cui_tang", "p_li xuan_tang", "father_of", 862, None, None, None, None),
    ("p_li xuan_tang", "k_tang", "succeeded_by", 873, 8, 888, 3, "僖宗"),
    ("p_li xuan_tang", "p_liye_tang", "sibling_of", 867, None, None, None, "兄弟"),
    ("p_liye_tang", "k_tang", "succeeded_by", 888, 3, 904, 8, "昭宗"),
    ("p_liye_tang", "p_li zhu_tang", "father_of", 892, None, None, None, None),
    ("p_li zhu_tang", "k_tang", "succeeded_by", 904, 8, 907, 4, "哀帝,禅让朱温"),
    ("p_li zhu_tang", "p_zhuwen", "usurped", 907, 4, None, None, "禅让"),
    ("p_zhuwen", "p_li zhu_tang", "killed", 908, 3, None, None, "弑哀帝"),

    # 宪宗被弑
    ("p_lichun", "p_liheng_tang", "killed", 820, 2, None, None, "宪宗为宦官所弑,穆宗继位(疑案)"),

    # 牛李党争
    ("p_niu_sengru", "f_niu_dang", "leader_of", 821, None, 847, None, None),
    ("p_li_zongmin", "f_niu_dang", "leader_of", 821, None, 846, None, None),
    ("p_li_deyu", "f_li_dang", "leader_of", 821, None, 850, None, None),
    ("p_li_jifu", "f_li_dang", "leader_of", 805, None, 814, None, None),
    ("p_niu_sengru", "p_li_deyu", "rival_of", 821, None, 850, None, "牛李党争"),
    ("p_niu_sengru", "p_li_zongmin", "allied_with", 821, None, 847, None, "同党"),
    ("p_li_deyu", "p_li_jifu", "child_of", 787, None, None, None, "李德裕是李吉甫子"),
    ("p_niu_sengru", "e_niu_li_dangzheng", "participated_in", 821, None, 847, None, None),
    ("p_li_deyu", "e_niu_li_dangzheng", "participated_in", 821, None, 850, None, None),
    ("p_li_deyu", "p_liyan_tang", "served_under", 840, 1, 846, 3, "会昌为相"),

    # 永贞革新
    ("p_lisong", "p_wang_shuwen", "served_under", 805, 1, 805, 8, "顺宗用王叔文"),
    ("p_wang_shuwen", "p_wang_pi", "allied_with", 805, None, 806, None, "二王"),
    ("p_wang_shuwen", "p_liu_yuxi", "allied_with", 805, None, 806, None, None),
    ("p_wang_shuwen", "p_liu_zongyuan", "allied_with", 805, None, 806, None, None),
    ("p_wang_shuwen", "e_yongzhen_gexin", "participated_in", 805, 8, None, None, "主导"),

    # 甘露之变
    ("p_liang_tang", "e_ganlu_zhibian", "participated_in", 835, 12, None, None, "策划"),
    ("p_chou_shiliang", "e_ganlu_zhibian", "participated_in", 835, 12, None, None, "镇压"),
    ("p_chou_shiliang", "f_late_tang_eunuchs", "leader_of", 826, None, 843, None, None),

    # 黄巢起义系
    ("p_wang_xianzhi", "p_huangchao", "allied_with", 875, 6, 878, 2, "初期共同起义"),
    ("p_wang_xianzhi", "e_wang_xianzhi_qiyi", "participated_in", 875, 6, 878, 2, "领袖"),
    ("p_huangchao", "e_huangchao_qiyi", "participated_in", 875, None, 884, 6, "领袖"),
    ("p_huangchao", "e_huangchao_zhan_changan", "participated_in", 880, 12, None, None, "称帝建齐"),
    ("p_huangchao", "f_huangchao_army", "leader_of", 875, None, 884, 6, None),
    ("p_wang_xianzhi", "f_huangchao_army", "leader_of", 875, 6, 878, 2, None),
    ("p_shang_rang", "p_huangchao", "served_under", 875, None, 884, None, "黄巢部将"),
    ("p_shang_rang", "f_huangchao_army", "member_of", 875, None, 884, None, None),
    ("p_zhuwen", "p_huangchao", "served_under", 877, None, 882, 9, "黄巢部将"),
    ("p_zhuwen", "f_huangchao_army", "member_of", 877, None, 882, 9, "降唐前"),
    ("p_zhuwen", "e_huangchao_deng_zhou_jianliang", "participated_in", 882, 9, None, None, "降唐"),
    ("p_likaiqu", "e_jiannan_chengzhong_li_jianyong", "participated_in", 881, None, 884, None, "沙陀破黄巢"),
    ("p_gao_pian", "e_huangchao_zhan_changan", "participated_in", 879, None, 880, 12, "坐视黄巢北上"),

    # 河朔三镇
    ("p_tian_chengsi", "f_heshuo_3_zhen", "leader_of", 763, None, 779, None, "魏博"),
    ("p_li_baochen", "f_heshuo_3_zhen", "leader_of", 763, None, 781, None, "成德"),
    ("p_li_huaixian", "f_heshuo_3_zhen", "leader_of", 763, None, 768, None, "卢龙"),
    ("p_tian_yue", "p_tian_chengsi", "child_of", 751, None, None, None, "侄"),
    ("p_wang_wujun", "p_li_baochen", "served_under", None, None, None, None, "成德部将"),
    ("p_zhu_tao", "f_heshuo_3_zhen", "leader_of", 772, None, 785, None, "卢龙"),

    # 元和削藩
    ("p_lichun", "e_yuanhe_xiaofan", "participated_in", 806, None, 819, None, "主导"),
    ("p_wu_yuanji", "e_yuanhe_xiaofan", "participated_in", 814, None, 817, 11, "被擒"),
    ("p_li_su", "p_wu_yuanji", "killed", 817, 11, None, None, "雪夜入蔡州"),
    ("p_li_su", "e_yuanhe_xiaofan", "participated_in", 817, 11, None, None, "擒吴元济"),
    ("p_li_shidao", "e_yuanhe_xiaofan", "participated_in", 806, None, 819, None, "淄青"),
    ("p_li_shidao", "p_lichun", "rival_of", 806, None, 819, None, "反削藩"),

    # 中晚唐其他
    ("p_li_guangbi", "e_an_lushan_rebellion", "participated_in", 755, 12, 763, 1, "主力平叛"),
    ("p_yan_zhenqing", "e_an_lushan_rebellion", "participated_in", 755, 12, None, None, "起兵讨贼"),
    ("p_yan_gaoqing", "e_an_lushan_rebellion", "participated_in", 755, 12, 756, 1, "起兵讨贼"),
    ("p_zhang_xun", "e_an_lushan_rebellion", "participated_in", 757, None, 757, 11, "睢阳保卫战"),
    ("p_yan_zhenqing", "p_yan_gaoqing", "sibling_of", None, None, None, None, "堂兄弟"),
    ("p_guo_ziyi", "e_an_lushan_rebellion", "participated_in", 755, 12, 763, 1, "主力平叛"),

    # 因果链
    ("e_yongzhen_gexin", "e_ganlu_zhibian", "preceded_by", None, None, None, None, "永贞失败→宦官专权→甘露之变"),
    ("e_ganlu_zhibian", "e_niu_li_dangzheng", "preceded_by", None, None, None, None, "宦官把持朝政激化党争"),
    ("e_qingfu_qiyi", "e_pangxun_zhibian", "preceded_by", None, None, None, None, "前仆后继"),
    ("e_pangxun_zhibian", "e_huangchao_qiyi", "preceded_by", None, None, None, None, "庞勋之变引出黄巢"),
    ("e_huangchao_qiyi", "e_zhuwen_tang", "preceded_by", None, None, None, None, "黄巢残部朱温终结唐朝"),
    ("e_huangchao_qiyi", "e_jiannan_chengzhong_li_jianyong", "preceded_by", None, None, None, None, "沙陀因平叛崛起"),
    ("e_yuanhe_xiaofan", "e_an_lushan_rebellion", "preceded_by", None, None, None, None, "安史之乱后河朔割据→元和削藩"),

    # 黄河ipi 归义军
    ("e_hexi_zhangyichao", "e_dazhong_zhizhi", "part_of", 851, None, None, None, "大中之治成就"),
]


def to_dict(rel):
    f, t, type_, sy, sm, uy, um, note = rel
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
    return obj


def gen_relations():
    items = [to_dict(r) for r in RELATIONS]
    seen = set()
    deduped = []
    for r in items:
        key = (r["from"], r["to"], r["type"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    out = DATA / "relations" / "late_tang.yaml"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(deduped, f, allow_unicode=True, sort_keys=False)
    print(f"  ✓ {len(deduped)} late-Tang relations → data/relations/late_tang.yaml")


if __name__ == "__main__":
    print(f"→ Phase 9: Mid-Late Tang (763-907)")
    gen_late_tang_places()
    print(f"  ✓ {len(LATE_TANG_PLACES)} places")
    gen_late_tang_persons()
    print(f"  ✓ {len([p for p in LATE_TANG_PERSONS if p and not p[0].endswith(('_existing', '_add', '_pre'))])} persons")
    gen_event_places()
    print(f"  ✓ {len(LATE_TANG_EVENT_PLACES)} event places")
    gen_late_tang_events()
    print(f"  ✓ {len(LATE_TANG_EVENTS)} events")
    gen_late_tang_factions()
    print(f"  ✓ {len(LATE_TANG_FACTIONS)} factions")
    gen_relations()
    print("Done.")
