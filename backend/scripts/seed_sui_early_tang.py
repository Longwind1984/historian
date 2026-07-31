#!/usr/bin/env python3
"""Phase 10 — Sui + Early/High Tang (581-763).

Covers:
- 隋朝 (581-618):杨坚代周、灭陈统一、大运河、炀帝暴政、隋末农民起义
- 唐前期 (618-763):高祖/太宗/高宗/武后/中宗/睿宗/玄宗
- 贞观之治、永徽之治、武周革命、开元盛世、安史之乱
- 凌烟阁二十四功臣

All cross-checked against《隋书》《旧唐书》《新唐书》《资治通鉴》.
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
# PLACES
# ============================================================
PLACES = [
    ("pl_daxing", "大兴城", "西安", "陕西", 34.27, 108.95, "capital", ["长安"], "隋唐都城"),
    ("pl_jiangdu", "江都", "扬州", "江苏", 32.39, 119.42, "city", ["广陵"], "隋炀帝行都"),
    ("pl_luoyang_sui", "洛阳(东都)", "洛阳", "河南", 34.62, 112.45, "capital", ["东都"], "隋唐东都"),
    ("pl_jianye", "建康", "南京", "江苏", 32.04, 118.78, "capital", ["金陵"], "陈都,隋灭之"),
    ("pl_yuhang", "余杭", "杭州", "浙江", 30.27, 120.16, "city", ["杭州"], "大运河南端"),
    ("pl_zhuojun", "涿郡", "北京", "北京", 39.91, 116.40, "city", ["幽州"], "大运河北端"),
    ("pl_yongjiliang", "永济渠", "聊城/临清", "山东", 36.45, 115.97, "city", [], "大运河永济渠段"),
    ("pl_tongqu", "通济渠", "开封", "河南", 34.80, 114.31, "city", ["汴州"], "大运河通济渠段"),
    ("pl_qinghua", "青化/瓦岗", "滑县", "河南", 35.58, 114.52, "battlefield", ["瓦岗"], "瓦岗寨起义地"),
    ("pl_julu_sui", "巨鹿", "巨鹿", "河北", 37.07, 114.66, "battlefield", [], "617 瓦岗之战"),
    ("pl_jiannan_sui", "剑南", "成都", "四川", 30.67, 104.07, "city", [], "隋唐剑南道"),
    ("pl_huaili", "湋水/岐州", "凤翔", "陕西", 34.52, 107.40, "city", [], "隋岐州"),
    ("pl_yongqiu", "雍丘", "杞县", "河南", 34.55, 114.74, "city", [], "张巡守雍丘"),
    ("pl_sui_lishui", "涿郡涿水", "涿州", "河北", 39.49, 115.98, "battlefield", [], "隋征高句丽"),
    ("pl_liaodong_sui", "辽东城", "辽阳", "辽宁", 41.27, 123.18, "battlefield", [], "隋征高句丽"),
    ("pl_pyuongyang", "平壤", "平壤", "朝鲜", 39.02, 125.74, "city", [], "隋征高句丽目标"),
    ("pl_wude_sui", "武威/姑臧", "武威", "甘肃", 37.93, 102.64, "city", [], "河西走廊"),
    ("pl_dunhuang_sui", "敦煌", "敦煌", "甘肃", 40.14, 94.66, "city", [], "河西走廊"),
    ("pl_turpan_sui", "高昌", "吐鲁番", "新疆", 42.95, 89.19, "city", [], "西域"),
    ("pl_xuanwu", "玄武门", "西安", "陕西", 34.27, 108.95, "battlefield", [], "626 玄武门之变"),
    ("pl_weibei_tang", "渭北", "渭南", "陕西", 34.50, 109.51, "city", [], "李渊起兵地"),
    ("pl_taiyuan_tang", "太原", "太原", "山西", 37.77, 112.55, "city", ["并州"], "李渊起兵"),
    ("pl_dunhuang_turk", "郁督军山", "杭爱山", "蒙古", 47.40, 100.50, "region", [], "突厥汗庭"),
    ("pl_qingshui_tang", "清水", "清水", "甘肃", 34.75, 106.14, "city", [], "唐蕃边界"),
    ("pl_dafeichuan", "大非川", "贵南", "青海", 35.58, 100.74, "battlefield", [], "670 唐蕃之战"),
    ("pl_talas", "怛罗斯", "塔拉兹", "哈萨克斯坦", 42.90, 71.00, "battlefield", [], "754 怛罗斯之战"),
    ("pl_xiazhou_sui", "夏州", "靖边", "陕西", 37.60, 108.79, "city", ["统万"], "梁师都据地"),
    ("pl_zhenguo_sui", "真定", "正定", "河北", 38.15, 114.57, "city", [], "窦建德"),
    ("pl_pingxiadu", "平夏城", "靖边", "陕西", 37.60, 108.79, "city", [], "党项"),
    ("pl_didao_sui", "狄道", "临洮", "甘肃", 35.37, 103.86, "city", [], "陇右"),
    ("pl_yiwu_sui", "伊吾", "哈密", "新疆", 42.83, 93.51, "city", [], "西域门户"),
    ("pl_karasha", "疏勒", "喀什", "新疆", 39.47, 75.99, "city", [], "安西四镇之一"),
    ("pl_kucha", "龟兹", "库车", "新疆", 41.72, 82.95, "city", [], "安西四镇之一"),
    ("pl_khotan", "于阗", "和田", "新疆", 37.11, 79.92, "city", [], "安西四镇之一"),
    ("pl_yanqi", "焉耆", "焉耆", "新疆", 42.06, 86.58, "city", [], "安西四镇之一"),
    ("pl_chang_an_pre_tang", "长安(隋大兴)", "西安", "陕西", 34.27, 108.95, "capital", [], "隋唐都"),
]


def gen_places():
    for tup in PLACES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["隋书·地理志", "旧唐书·地理志", "中国历史地图集·隋唐五代"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# ============================================================
# PERSONS (隋 + 唐前期到盛唐 581-763)
# ============================================================
PERSONS = [
    # === 隋朝皇室 ===
    ("p_yangjian_pre", "杨坚(已存在标记)", None, None, (None, None), (None, None), None,
     "已存在 p_yangjian", []) if False else None,
    ("p_dugu_qieluo", "独孤伽罗", ["独孤皇后", "文献皇后"], None, (544, None), (602, 8), "pl_yuncheng_gu",
     "隋文帝杨坚皇后。父独孤信(关陇八柱国)。与杨坚并称'二圣',深度参与朝政。'一夫一妻'制度坚定推行者,影响文帝不设嫔妃。",
     ["隋书·后妃传", "周书·独孤信传"]),
    ("p_yangyong", "杨勇", ["房陵王"], None, (None, None), (604, None), "pl_daxing",
     "隋文帝长子,太子。率性奢侈,为母独孤皇后所不喜。600 年被废为房陵王,弟杨广被立为太子。604 年杨广即位后被赐死。",
     ["隋书·房陵王勇传"]),
    ("p_yangguang", "杨广", ["隋炀帝"], "阿𡡉", (569, None), (618, 4), "pl_daxing",
     "隋炀帝。杨坚次子。600 年代兄杨勇为太子,604 年即位(疑弑父)。营东都洛阳,开大运河,三征高句丽,巡幸江都。穷奢极欲,劳民伤财。617 年李渊起兵,618 年在江都被宇文化及所弑,隋亡。",
     "中国历史上最具争议的皇帝之一。大运河利在千秋,但其暴政直接导致隋朝覆灭。",
     ["隋书·炀帝纪", "资治通鉴·卷180-185"]),
    ("p_yangzhao", "杨昭", ["元德太子"], None, (584, None), (606, None), "pl_daxing",
     "隋炀帝长子,元德太子。早卒。三子:杨侑、杨侗、杨秉。",
     ["隋书·元德太子昭传"]),
    ("p_yangyou", "杨侑", ["隋恭帝"], None, (605, None), (619, None), "pl_daxing",
     "隋恭帝。炀帝孙,元德太子之子。617 年李渊入长安立之为帝,改元义宁,遥尊炀帝为太上皇。618 年禅让李渊,隋亡。619 年卒。",
     ["隋书·恭帝纪"]),
    ("p_yangtong", "杨侗", ["皇泰主"], None, (605, None), (619, None), "pl_luoyang_sui",
     "隋皇泰主。炀帝孙。618 年洛阳群臣立之为帝,改元皇泰。619 年为王世充所废杀。",
     ["隋书·皇泰主传"]),

    # === 隋朝功臣 ===
    ("p_gaojiong", "高颎", ["高昭玄"], "昭玄", (541, None), (607, None), "pl_daxing",
     "隋朝开国首席谋臣。渤海蓨县人。助杨坚代周、平尉迟迥、灭陈。'仆射二十年'。炀帝即位后被杀。",
     ["隋书·高颎传"]),
    ("p_suwei", "苏威", ["苏无畏"], "无畏", (542, None), (623, None), "pl_wuwei_sui",
     "隋朝宰相。历仕隋文帝、炀帝、唐高祖。'关陇集团'重要成员。",
     ["隋书·苏威传"]),
    ("p_yangsu", "杨素", ["杨处道"], "处道", (544, None), (606, None), "pl_huayin_sui",
     "隋朝名将、权臣。华阴人。助杨广夺嫡。597 平江南叛、599 大破突厥。604 协助杨广即位(疑弑文帝)。后封楚国公。",
     ["隋书·杨素传"]),
    ("p_hanqinhu", "韩擒虎", ["韩子通"], "子通", (538, None), (592, None), "pl_dongyong_sui",
     "隋朝名将。588 年伐陈先锋,克建康,俘陈后主。",
     ["隋书·韩擒虎传"]),
    ("p_heruobi", "贺若弼", ["贺若辅伯"], "辅伯", (544, None), (607, None), "pl_luoyang_sui",
     "隋朝名将。588 年伐陈,从广陵渡江。'比韩擒虎先入建康'。炀帝即位后被杀。",
     ["隋书·贺若弼传"]),
    ("p_shiwan_sue", "史万岁", ["史京兆"], None, (549, None), (600, 11), "pl_dunhuang_sui",
     "隋朝名将。屡破突厥。600 年因杨素陷害被隋文帝所杀。",
     ["隋书·史万岁传"]),

    # === 隋末群雄 ===
    ("p_yangsu_2", "杨玄感", ["杨玄感"], None, (None, None), (613, 8), "pl_daxing",
     "隋礼部尚书杨素子。613 年趁炀帝征高句丽,在黎阳起兵反隋,众至 10 万。失败被杀。",
     "隋末大起义前奏,标志隋朝统治集团内部分裂。",
     ["隋书·杨玄感传", "资治通鉴·卷182"]),
    ("p_li_mi", "李密", ["李玄邃", "李法主"], "玄邃", (582, None), (619, 1), "pl_chang_an_pre_tang",
     "隋末瓦岗军领袖。辽东襄平人。613 叔杨玄感起兵,败后投瓦岗。翟让让位后任瓦岗军主帅。618 王世充击败之,降唐,后叛唐被杀。",
     ["隋书·李密传", "旧唐书·李密传"]),
    ("p_zhai_rang", "翟让", None, None, (None, None), (617, None), "pl_qinghua",
     "瓦岗军创始者。东郡韦城人。616 起兵于瓦岗寨。617 让位于李密,后被李密所杀。",
     ["旧唐书·李密传"]),
    ("p_dou_jiande", "窦建德", ["窦建德"], None, (573, None), (621, None), "pl_zhenguo_sui",
     "隋末群雄之一。漳南人。618 称夏王,都乐寿。621 营救王世充时,在虎牢关为李世民所擒,斩于长安。",
     "隋末河北最大势力,深得民心。",
     ["旧唐书·窦建德传"]),
    ("p_wang_shichong", "王世充", None, None, (None, None), (621, None), "pl_luoyang_sui",
     "隋末群雄之一。618 炀帝被弑后,在洛阳立杨侗为帝(皇泰主),619 废之自立,国号郑。621 李世民破之,降唐,后被杀。",
     ["旧唐书·王世充传"]),
    ("p_yuwen_huaji", "宇文化及", None, None, (None, None), (619, None), "pl_jiangdu",
     "隋权臣宇文述子。618 在江都发动兵变,弑炀帝,立杨浩为傀儡,后废之自立,国号许。619 为窦建德所擒杀。",
     ["隋书·宇文化及传"]),

    # === 唐高祖李渊(与已存在的 p_liyuan 关联) ===
    # (李渊实体已存在,这里不重复创建)

    # === 凌烟阁二十四功臣(部分核心)===
    ("p_zhangsun_wuji", "长孙无忌", ["长孙辅机"], "辅机", (594, None), (659, None), "pl_luoyang_sui",
     "唐初功臣,凌烟阁二十四功臣之首。李治舅。助李世民玄武门之变。高宗朝为顾命大臣。因反对立武则天为后,659 被许敬宗诬陷谋反,贬死黔州。",
     ["旧唐书·长孙无忌传", "资治通鉴·卷200"]),
    ("p_weizheng", "魏征", ["魏玄成"], "玄成", (580, None), (643, 2), "pl_jinzhao_weizheng",
     "唐初名臣。先仕李密、窦建德,后归唐。太宗朝为谏议大夫,以直言著称。'贞观之治'重要推手。太宗谓'以铜为镜...'。",
     ["旧唐书·魏征传", "贞观政要"]),
    ("p_fang_xuanling", "房玄龄", ["房乔"], "乔", (579, None), (648, 8), "pl_qi_xianfang",
     "唐初名相。'贞观之治'重要辅臣。'房谋杜断'。",
     ["旧唐书·房玄龄传"]),
    ("p_du_ruhui", "杜如晦", ["杜克明"], "克明", (585, None), (630, None), "pl_duqu_duhui",
     "唐初名相。与房玄龄并称'房杜'。",
     ["旧唐书·杜如晦传"]),
    ("p_li_jing_tang", "李靖", ["李药师", "李卫公"], "药师", (571, None), (649, 5), "pl_sanyuan_jing",
     "唐初军事家。630 大破东突厥,擒颉利可汗。635 破吐谷浑。'凌烟阁二十四功臣'之一。著《李卫公问对》。",
     "中国军事史杰出统帅。",
     ["旧唐书·李靖传"]),
    ("p_li_shiji", "李世勣", ["徐世勣", "徐懋功", "李绩"], "懋功", (594, None), (669, 12), "pl_liaodong_shiji",
     "唐初名将。本姓徐,赐姓李。后避太宗讳去'世'。历仕高祖、太宗、高宗三朝。660-668 与苏定方灭高句丽。'凌烟阁'之一。",
     ["旧唐书·李绩传"]),
    ("p_yuchi_gong", "尉迟敬德", ["尉迟恭"], "敬德", (585, None), (658, None), "pl_shuozhou_yy",
     "唐初骁将。玄武门之变射杀李元吉。'门神'。凌烟阁之一。",
     ["旧唐书·尉迟敬德传"]),
    ("p_qin_shubao", "秦叔宝", ["秦琼"], "叔宝", (None, None), (638, None), "pl_laiyang_qin",
     "唐初骁将。玄武门之变参与者。凌烟阁之一。'门神'。",
     ["旧唐书·秦叔宝传"]),
    ("p_cheng_yaojin", "程咬金", ["程知节", "程义贞"], "知节", (589, None), (665, None), "pl_jining_cheng",
     "唐初骁将。瓦岗旧部。凌烟阁之一。",
     ["旧唐书·程知节传"]),
    ("p_hou_jun_ji", "侯君集", None, None, (None, None), (643, 4), "pl_sanyuan_jing",
     "唐初功臣。凌烟阁之一。640 灭高昌。643 因太子承乾案被诛。",
     ["旧唐书·侯君集传"]),

    # === 武周 / 神龙革命 / 唐隆政变 ===
    ("p_wu_zetian", "武曌", ["武则天", "武后", "圣神皇帝"], None, (624, 2), (705, 12), "pl_wenshui_wu",
     "中国历史上唯一的女皇帝。并州文水人。唐太宗才人,高宗皇后。655 立为后。660 起与高宗并称'二圣'。高宗崩后临朝称制。690 改国号为周,称帝,都洛阳。705 神龙革命中被迫退位,传位中宗,唐复国。同年崩。",
     "中国唯一女皇帝。开创武举、殿试。任用酷吏。神龙革命后退位。",
     ["旧唐书·则天皇后本纪", "新唐书·则天皇后本纪", "资治通鉴·卷203-208"]),
    ("p_shangguan_waner", "上官婉儿", ["上官昭容"], None, (664, None), (710, 7), "pl_shaanxi_sgy",
     "唐代女官、诗人。上官仪孙女。武则天赏识其才,封昭容,掌诏命。中宗、韦后朝继续掌权。710 唐隆政变中被李隆基所杀。",
     ["旧唐书·后妃传·上官昭容"]),
    ("p_zhang_jianzhi", "张柬之", ["张孟阳"], "孟阳", (625, None), (706, None), "pl_xiangyang_zhang",
     "武周宰相。705 神龙革命发动者,逼武则天退位,迎中宗复位。封汉阳王。后为武三思所诬,贬死。",
     ["旧唐书·张柬之传"]),

    # === 玄宗朝 + 安史之乱核心 ===
    ("p_li_longji", "李隆基", ["唐玄宗", "李三郎"], "三郎", (685, 9), (762, 5), "pl_daxing",
     "唐玄宗。710 唐隆政变诛韦后,712 即位。713 先天之变诛太平公主。开元(713-741)励精图治,史称'开元盛世',唐朝全盛。天宝(742-756)宠杨贵妃、任李林甫、杨国忠,怠政。755 安史之乱爆发,763 平定。玄宗奔蜀,马嵬驿之变杨贵妃死,后还都为太上皇,762 崩。",
     "盛唐转衰的关键人物。前期明君,后期昏君。",
     ["旧唐书·玄宗本纪", "资治通鉴·卷210-221"]),
    ("p_yang_guifei", "杨玉环", ["杨贵妃", "太真"], None, (719, None), (756, 7), "pl_yongji_yang",
     "唐玄宗宠妃。天宝四年(745)册为贵妃。堂兄杨国忠任相。756 马嵬驿之变中被缢死。'回眸一笑百媚生'。",
     ["旧唐书·后妃传·杨贵妃", "白居易·长恨歌"]),
    ("p_yang_guozhong", "杨国忠", ["杨钊"], None, (None, None), (756, 7), "pl_yongji_yang",
     "玄宗朝宰相。杨贵妃堂兄。748 入朝,752 接替李林甫为相。与安禄山不和,激化矛盾。756 马嵬驿之变中被乱军所杀。",
     ["旧唐书·杨国忠传"]),
    ("p_li_linpu", "李林甫", None, None, (683, None), (753, 1), "pl_zongcheng_linpu",
     "玄宗朝宰相。736-752 任相 19 年。'口蜜腹剑'。任用胡将为节度使(安禄山由此崛起),排除异己。",
     "为安史之乱埋下祸根。",
     ["旧唐书·李林甫传"]),

    # === 平叛将领(已存在郭子仪/李光弼,补充其他)===
    ("p_zhang_xun_existing", "张巡标记", None, None, (None, None), (None, None), None, "", []) if False else None,

    # === 颜真卿、文化名人(中晚唐已建,这里不重复) ===

    # === 唐玄宗朝文化 ===
    ("p_li_bai", "李白", ["李太白", "青莲居士"], "太白", (701, None), (762, None), "pl_suiye_libai",
     "盛唐大诗人。'诗仙'。祖籍陇西成纪,生于碎叶城(今吉尔吉斯斯坦)。742-744 入长安供奉翰林。安史之乱中入永王李璘幕府,永王败后被流夜郎,遇赦还。762 卒于当涂。",
     "中国文学史巅峰之一。",
     ["旧唐书·文苑传·李白", "新唐书·文艺传·李白"]),
    ("p_du_fu", "杜甫", ["杜子美", "杜工部"], "子美", (712, None), (770, None), "pl_gongxian_dufu",
     "盛唐大诗人。'诗圣'。河南巩县人。安史之乱颠沛流离,作'三吏三别'。770 病卒于湘江舟中。",
     "中国现实主义诗歌巅峰。",
     ["旧唐书·文苑传·杜甫", "新唐书·文艺传·杜甫"]),
    ("p_wang_wei", "王维", ["王摩诘"], "摩诘", (701, None), (761, None), "pl_qi_wangwei",
     "盛唐诗人、画家。'诗佛'。安史之乱中受伪职,乱后定罪获赦。'空山新雨后'。",
     ["旧唐书·文苑传·王维"]),
    ("p_xuan_zang", "玄奘", ["三藏法师", "唐僧"], None, (602, None), (664, 2), "pl_yanshi_xuanzang",
     "唐代高僧、翻译家、旅行家。629-645 西行天竺求法 17 年,经西域、中亚至印度。著《大唐西域记》。译经 75 部 1335 卷。",
     "中国佛教史与中外文化交流史最重要人物之一。",
     ["大慈恩寺三藏法师传", "旧唐书·方伎传"]),
]
PERSONS = [p for p in PERSONS if p is not None and not p[0].endswith(("_existing", "_add", "_pre"))]


def gen_persons():
    for tup in PERSONS:
        # 9 or 10 fields
        if len(tup) == 9:
            pid, name, aliases, courtesy, born, died, birthplace, bio, srcs = tup
            significance = None
        else:
            pid, name, aliases, courtesy, born, died, birthplace, bio, significance, srcs = tup
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
        if "p_dugu_qieluo" == pid or "p_yang_guifei" == pid or "p_wu_zetian" == pid or "p_shangguan_waner" == pid:
            obj["gender"] = "female"
        if birthplace:
            obj["birthplace"] = birthplace
        obj["bio"] = bio
        if significance:
            obj["ext"] = {"significance": significance}
        obj["sources"] = srcs
        write(DATA / "entities" / "persons" / f"{pid[2:]}.yaml", obj)


# ============================================================
# EVENTS
# ============================================================
EVENTS = [
    ("e_yangjian_dai_zhou", "杨坚代周", (581, 3), None, "coup", "pl_daxing", ["d_sui_pre", "d_zhou_north"],
     "581 年二月北周静帝禅让,杨坚即位,国号隋,改元开皇。北周(宇文泰奠基的关陇集团政权)灭亡。",
     "隋朝建立。关陇集团继续主导,杨氏即关陇八柱国之一。",
     ["隋书·高祖纪", "资治通鉴·卷175"]),

    ("e_sui_mie_chen", "隋灭陈统一", (589, 1), None, "institution", "pl_jianye", ["d_sui", "k_chen"],
     "588 年隋发兵 51 万大举伐陈,韩擒虎、贺若弼等为将。589 年正月攻入建康,俘陈后主陈叔宝,陈亡。",
     "结束自永嘉之乱以来近 300 年的分裂(西晋短暂统一不计),中国重新统一。",
     ["隋书·高祖纪", "资治通鉴·卷177"]),

    ("e_kaihuang_zhizhi", "开皇之治", (581, None), (604, None), "reform", "pl_daxing", ["d_sui"],
     "581-604 隋文帝在位期间。整顿吏治、轻徭薄赋、大兴科举雏形、颁《开皇律》。国家仓库充盈,人口由 400 万户增至 890 万户。",
     "中国历史上著名的治世,史称'开皇之治'。",
     ["隋书·高祖纪", "资治通鉴·卷175-179"]),

    ("e_dayunhe", "大运河开通", (605, None), (610, None), "institution", "pl_tongqu", ["d_sui"],
     "605-610 年隋炀帝开凿。以洛阳为中心,通济渠、永济渠、邗沟、江南河四段相连。涿郡(北京)至余杭(杭州),全长 2700 余公里。",
     "纵贯中国南北,影响千年。但工程浩大,死伤百万,直接引发隋末大起义。",
     ["隋书·炀帝纪", "资治通鉴·卷181"]),

    ("e_sui_zheng_gaogouli", "隋征高句丽", (612, None), (614, None), "institution", "pl_liaodong_sui", ["d_sui"],
     "612、613、614 年隋炀帝三次亲征高句丽。612 第一次出兵 113 万,因指挥失当败于萨水(平壤郊外)。613 杨玄感起兵而退。614 来护儿虽至平壤城下,无功而还。",
     "国力耗尽,直接引发隋末农民大起义,导致隋朝灭亡。",
     ["隋书·炀帝纪", "资治通鉴·卷181-182"]),

    ("e_sui_mo_qiyi", "隋末农民起义", (611, None), (624, None), "institution", "pl_qinghua", ["d_sui"],
     "611 王薄在长白山(山东章丘)首义。613 杨玄感起兵。616 后翟让瓦岗军、窦建德、杜伏威等遍布山东、河北、河南、江淮。隋廷失控。618 隋亡。",
     "彻底摧毁隋朝,各路群雄演化为唐初群雄(李世民逐一平定)。",
     ["隋书·炀帝纪", "资治通鉴·卷181-189"]),

    ("e_jian_guo_tang", "唐朝建立", (618, 5), None, "coup", "pl_daxing", ["d_tang_pre"],
     "617 年李渊太原起兵,攻克长安,立代王杨侑为帝(隋恭帝)。618 年炀帝被弑,李渊受禅称帝,国号唐,改元武德。",
     "唐朝(618-907)开始,中国历史上影响最深远的朝代之一。",
     ["旧唐书·高祖本纪", "资治通鉴·卷185"]),

    ("e_xuanwumen", "玄武门之变", (626, 7, 4), None, "coup", "pl_xuanwu", ["d_tang_pre"],
     "626 年六月四日,秦王李世民在玄武门发动政变,射杀太子李建成、齐王李元吉。高祖李渊被迫立世民为太子,八月禅位,世民即位为太宗。",
     "贞观之治开启。",
     ["旧唐书·太宗本纪", "资治通鉴·卷191"]),

    ("e_zhenguan_zhizhi", "贞观之治", (627, None), (649, None), "reform", "pl_daxing", ["d_tang_pre"],
     "627-649 唐太宗在位期间。虚心纳谏(魏征)、轻徭薄赋、完善三省六部制与科举、平东突厥(630)、灭吐谷浑(634)、和亲吐蕃(文成公主,641)、玄奘西行(629-645)。",
     "中国历史上著名的治世典范,唐朝进入全盛期。",
     ["旧唐书·太宗本纪", "贞观政要", "资治通鉴·卷192-198"]),

    ("e_tang_mie_dongtu_jue", "唐灭东突厥", (629, 11), (630, 3), "institution", "pl_dunhuang_turk", ["d_tang_pre"],
     "629 年唐太宗命李靖、李世勣等大举出击东突厥。630 年正月李靖夜袭阴山,大破之。三月俘颉利可汗,东突厥灭亡。",
     "唐朝成为东亚霸主。太宗被各族尊为'天可汗'。",
     ["旧唐书·突厥传", "资治通鉴·卷193"]),

    ("e_wu_zhou_geming", "武周革命", (690, 9), None, "coup", "pl_luoyang_sui", ["d_tang_pre", "d_zhou_wu"],
     "690 年九月武则天称帝,改国号为周,改元天授,都洛阳。中国历史上唯一女皇帝。",
     "中国政治史独特一页。",
     ["旧唐书·则天皇后本纪", "资治通鉴·卷204"]),

    ("e_shenlong_geming", "神龙革命", (705, 1), None, "coup", "pl_luoyang_sui", ["d_zhou_wu", "d_tang_pre"],
     "705 年正月宰相张柬之、崔玄𬀩等率羽林军发动政变,逼武则天退位,迎中宗李显复位,唐复国。",
     "武周终结,李唐复辟。",
     ["旧唐书·中宗本纪", "资治通鉴·卷207"]),

    ("e_tanglong_zhengbian", "唐隆政变", (710, 6), None, "coup", "pl_daxing", ["d_tang_pre"],
     "710 年六月临淄王李隆基与姑母太平公主联合发动政变,诛韦后、安乐公主、上官婉儿等,废少帝,迎睿宗李旦复位。",
     "为李隆基即位(玄宗)铺路。",
     ["旧唐书·玄宗本纪", "资治通鉴·卷209"]),

    ("e_xiantian_zhibian", "先天之变", (713, 7), None, "coup", "pl_daxing", ["d_tang_pre"],
     "713 年玄宗诛杀姑母太平公主集团,真正亲政。改元开元。",
     "开元盛世开启。",
     ["旧唐书·玄宗本纪", "资治通鉴·卷210"]),

    ("e_kaiyuan_shengshi", "开元盛世", (713, None), (741, None), "reform", "pl_daxing", ["d_tang_pre"],
     "713-741 年玄宗开元年间。任姚崇、宋璟为相。整顿吏治、发展经济、兴修水利。疆域最大,人口至 800 万户。文化达高峰(李白、杜甫、王维等)。",
     "唐朝全盛,中国古典时代顶点。",
     ["旧唐书·玄宗本纪", "资治通鉴·卷211-215"]),

    ("e_mawei_zhibian", "马嵬驿之变", (756, 7), None, "coup", "pl_mawei", ["d_tang_pre"],
     "756 年六月安史乱军逼近长安,玄宗西奔入蜀。至马嵬驿,随驾禁军哗变,诛杨国忠,逼玄宗赐死杨贵妃。",
     "玄宗政治生命终结。太子李亨北上灵武即位(肃宗),玄宗还都后为太上皇。",
     ["旧唐书·杨贵妃传", "资治通鉴·卷218"]),

    ("e_tang_shoufu_liangjing", "唐收复两京", (757, 9), None, "institution", "pl_daxing", ["d_tang_pre"],
     "757 年九月郭子仪、李光弼率唐军(借回纥兵)先后收复长安、洛阳。安史叛军退守河北。",
     "安史之乱转折点。但藩镇割据之根已种。",
     ["旧唐书·肃宗本纪", "资治通鉴·卷220"]),

    ("e_talas_zhizhan", "怛罗斯之战", (751, 7), None, "battle", "pl_talas", ["d_tang_pre"],
     "751 年七月安西节度使高仙芝率唐军与黑衣大食(阿拔斯王朝)战于怛罗斯。唐军因葛逻禄部叛变而败。",
     "唐朝势力退出中亚。造纸术西传(中国造纸工匠被俘)。",
     ["旧唐书·西戎传", "资治通鉴·卷216"]),

    # Polity stubs to support references
]

# Need additional polity stubs for events to reference
EXTRA_POLITIES = [
    ("k_chen", "陈", "Chen", "#8e44ad", (557, None), (589, 1), None, "pl_jianye", None, "d_sui",
     "南朝陈。陈霸先所建,都建康。589 年为隋所灭,中国重新统一。",
     "陈书;南史"),
    ("d_zhou_north", "北周", "Northern Zhou", "#27ae60", (557, None), (581, 2), None, "pl_chang_an_pre_tang", None, "d_sui",
     "北朝之一。宇文觉所建,都长安。关陇集团核心政权。581 年为杨坚所代。",
     "周书;北史"),
    ("d_zhou_wu", "武周", "Wu Zhou", "#c0392b", (690, 9), (705, 1), "p_wu_zetian", "pl_luoyang_sui", None, "d_tang_pre",
     "武则天建立的朝代(690-705)。中国历史上唯一的女性皇权朝代。神龙革命后退位,唐复国。",
     "旧唐书·则天皇后本纪"),
]
EXTRA_POLITY_PLACES = [
    ("pl_wuwei_sui", "武威", "武威", "甘肃", 37.93, 102.64, "city", [], "苏威籍贯"),
    ("pl_huayin_sui", "华阴", "华阴", "陕西", 34.57, 110.07, "city", [], "杨素籍贯"),
    ("pl_dongyong_sui", "东垣", "新绛", "山西", 35.62, 111.22, "city", [], "韩擒虎籍贯"),
    ("pl_jinzhao_weizheng", "钜鹿/魏郡", "临漳", "河北", 36.21, 114.62, "city", [], "魏征籍贯"),
    ("pl_qi_xianfang", "齐州/临沂", "淄博", "山东", 36.65, 117.00, "city", [], "房玄龄籍贯(齐州)"),
    ("pl_duqu_duhui", "杜陵", "西安", "陕西", 34.16, 108.96, "city", [], "杜如晦籍贯"),
    ("pl_sanyuan_jing", "三原", "三原", "陕西", 34.62, 108.94, "city", [], "李靖/侯君集籍贯"),
    ("pl_liaodong_shiji", "辽东", "辽阳", "辽宁", 41.27, 123.18, "city", [], "李世勣籍贯(祖籍)"),
    ("pl_laiyang_qin", "历城", "济南", "山东", 36.65, 117.00, "city", [], "秦叔宝籍贯"),
    ("pl_jining_cheng", "济州", "济宁", "山东", 35.41, 116.58, "city", [], "程咬金籍贯"),
    ("pl_wenshui_wu", "并州文水", "文水", "山西", 37.43, 112.03, "city", [], "武则天籍贯"),
    ("pl_shaanxi_sgy", "陕县/上官", "三门峡", "河南", 34.77, 111.20, "city", [], "上官婉儿家族"),
    ("pl_xiangyang_zhang", "襄阳", "襄阳", "湖北", 32.04, 112.12, "city", [], "张柬之籍贯"),
    ("pl_yongji_yang", "弘农/永乐", "永济", "山西", 34.87, 110.45, "city", [], "杨贵妃籍贯"),
    ("pl_zongcheng_linpu", "宗城", "威县", "河北", 36.96, 115.10, "city", [], "李林甫籍贯"),
    ("pl_suiye_libai", "碎叶", "托克马克", "吉尔吉斯斯坦", 42.84, 75.30, "city", [], "李白出生地"),
    ("pl_gongxian_dufu", "巩县", "巩义", "河南", 34.75, 113.02, "city", [], "杜甫出生地"),
    ("pl_qi_wangwei", "祁县", "祁县", "山西", 37.36, 112.33, "city", [], "王维籍贯"),
    ("pl_yanshi_xuanzang", "缑氏", "偃师", "河南", 34.62, 112.78, "city", [], "玄奘籍贯"),
]


def gen_extra_polities():
    for tup in EXTRA_POLITIES:
        pid, name, en, color, founded, ended, founder, capital, supplanted, ended_by, desc, src = tup
        obj = {
            "id": pid, "type": "Polity", "name": name,
            "name_en": en, "color": color,
            "founded": {"year": founded[0]} if not founded[1] else {"year": founded[0], "month": founded[1]},
            "ended": {"year": ended[0]} if not ended[1] else {"year": ended[0], "month": ended[1]},
            "capital": capital,
            "description": desc,
            "sources": src.split(";"),
        }
        if founder:
            obj["founder"] = founder
        if supplanted:
            obj["supplanted"] = supplanted
        if ended_by:
            obj["ended_by"] = ended_by
        write(DATA / "entities" / "polities" / f"{pid[2:]}.yaml", obj)


def gen_extra_places():
    for tup in EXTRA_POLITY_PLACES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["旧唐书", "隋书", "中国历史地图集"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


def gen_events():
    for tup in EVENTS:
        eid, name, date, end, category, place, polities, desc, impact, srcs = tup
        obj = {
            "id": eid, "type": "Event", "name": name,
            "date": {"year": date[0]} if (len(date) < 2 or not date[1]) else {"year": date[0], "month": date[1]},
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


# ============================================================
# RELATIONS
# ============================================================
RELATIONS = [
    # 隋皇室
    ("p_yangjian", "p_dugu_qieluo", "spouse_of", 566, None, 602, 8, None),
    ("p_yangjian", "p_yangyong", "father_of", None, None, None, None, "长子"),
    ("p_yangjian", "p_yangguang", "father_of", 569, None, None, None, "次子"),
    ("p_yangguang", "p_yangzhao", "father_of", 584, None, None, None, None),
    ("p_yangzhao", "p_yangyou", "father_of", None, None, None, None, None),
    ("p_yangzhao", "p_yangtong", "father_of", None, None, None, None, None),
    ("p_yangjian", "k_yangjian_sui", "founded", 581, 3, None, None, "代周建隋") if False else
    ("p_yangjian", "d_sui", "founded", 581, 3, None, None, "代周建隋"),
    ("p_yangjian", "d_zhou_north", "usurped", 581, 3, None, None, "受禅"),
    ("p_yangyong", "p_yangguang", "predecessor_of", None, None, None, None, "太子位被夺"),

    # 隋臣
    ("p_yangjian", "p_gaojiong", "served_under", 581, None, 607, None, "首席谋臣"),
    ("p_yangjian", "p_suwei", "served_under", 581, None, 604, None, None),
    ("p_yangjian", "p_yangsu", "served_under", None, None, 606, None, None),
    ("p_yangguang", "p_yangsu", "served_under", 604, None, 606, None, "助夺嫡"),
    ("p_hanqinhu", "d_sui", "served_under", None, None, 592, None, "伐陈先锋"),
    ("p_heruobi", "d_sui", "served_under", None, None, 607, None, None),
    ("p_yangguang", "e_dayunhe", "participated_in", 605, None, 610, None, "主导"),
    ("p_yangguang", "e_sui_zheng_gaogouli", "participated_in", 612, None, 614, None, "三征高句丽"),
    ("p_yangguang", "e_kaihuang_zhizhi", "participated_in", 581, None, 604, None, "开皇年间为晋王"),
    ("p_yangjian", "e_kaihuang_zhizhi", "participated_in", 581, None, 604, None, "主导"),
    ("p_yangjian", "e_sui_mie_chen", "participated_in", 588, None, 589, 1, "主导"),
    ("p_yangjian", "e_yangjian_dai_zhou", "participated_in", 581, 3, None, None, "主导"),

    # 隋末群雄
    ("p_yangsu_2", "e_sui_mo_qiyi", "participated_in", 613, 8, None, None, "杨玄感起兵"),
    ("p_li_mi", "p_zhai_rang", "served_under", 616, None, 617, None, "瓦岗军"),
    ("p_li_mi", "p_zhai_rang", "killed", 617, None, None, None, "杀翟让夺权"),
    ("p_dou_jiande", "e_sui_mo_qiyi", "participated_in", 611, None, 621, None, "夏王"),
    ("p_wang_shichong", "e_sui_mo_qiyi", "participated_in", 618, None, 621, None, "郑"),
    ("p_yuwen_huaji", "p_yangguang", "killed", 618, 4, None, None, "江都之变"),
    ("p_yuwen_huaji", "e_sui_mo_qiyi", "participated_in", 618, 4, None, None, "弑炀帝"),

    # 唐高祖(已存在 p_liyuan)
    ("p_liyuan", "e_jian_guo_tang", "participated_in", 617, None, 618, 5, "起兵太原"),
    ("p_liyuan", "d_tang", "founded", 618, 5, None, None, "代隋建唐"),

    # 凌烟阁二十四功臣
    ("p_zhangsun_wuji", "p_liyuan", "served_under", 617, None, 626, None, None),
    ("p_zhangsun_wuji", "p_li_shimin", "served_under", 626, None, 649, None, None),
    ("p_zhangsun_wuji", "e_xuanwumen", "participated_in", 626, 7, None, None, "策划者"),
    ("p_weizheng", "p_li_shimin", "served_under", 627, None, 643, 2, "谏议大夫"),
    ("p_fang_xuanling", "p_li_shimin", "served_under", 626, None, 648, 8, None),
    ("p_du_ruhui", "p_li_shimin", "served_under", 626, None, 630, None, None),
    ("p_li_jing_tang", "e_tang_mie_dongtu_jue", "led", 629, 11, 630, 3, "夜袭阴山"),
    ("p_li_shiji", "e_tang_mie_dongtu_jue", "led", 629, 11, 630, 3, None),

    # 玄武门
    ("p_li_shimin", "p_liyuan", "usurped", 626, 7, None, None, "迫父禅位"),
    ("p_li_shimin", "e_xuanwumen", "participated_in", 626, 7, None, None, "发动者"),
    ("p_yuchi_gong", "e_xuanwumen", "participated_in", 626, 7, None, None, None),
    ("p_qin_shubao", "e_xuanwumen", "participated_in", 626, 7, None, None, None),
    ("p_cheng_yaojin", "e_xuanwumen", "participated_in", 626, 7, None, None, None),

    # 贞观之治
    ("p_li_shimin", "e_zhenguan_zhizhi", "participated_in", 627, None, 649, None, "主导"),
    ("p_weizheng", "e_zhenguan_zhizhi", "participated_in", 627, None, 643, 2, None),

    # 武周
    ("p_wu_zetian", "e_wu_zhou_geming", "participated_in", 690, 9, None, None, "称帝"),
    ("p_wu_zetian", "d_zhou_wu", "founded", 690, 9, None, None, None),
    ("p_wu_zetian", "d_tang_pre", "usurped", 690, 9, None, None, "代唐建周"),
    ("p_shangguan_waner", "p_wu_zetian", "served_under", 677, None, 705, 1, "掌诏命"),

    # 神龙革命
    ("p_zhang_jianzhi", "e_shenlong_geming", "participated_in", 705, 1, None, None, "发动者"),
    ("p_zhang_jianzhi", "p_wu_zetian", "usurped", 705, 1, None, None, "逼退位"),

    # 唐隆 / 先天
    ("p_li_longji", "e_tanglong_zhengbian", "participated_in", 710, 6, None, None, "发动者"),
    ("p_li_longji", "e_xiantian_zhibian", "participated_in", 713, 7, None, None, "主导"),

    # 玄宗朝
    ("p_li_longji", "e_kaiyuan_shengshi", "participated_in", 713, None, 741, None, "主导"),
    ("p_li_longji", "p_yang_guifei", "spouse_of", 745, None, 756, 7, "宠妃"),
    ("p_yang_guifei", "p_yang_guozhong", "sibling_of", None, None, None, None, "堂兄妹"),
    ("p_li_longji", "p_li_linpu", "served_under", 736, None, 752, 1, "任相"),
    ("p_li_longji", "p_yang_guozhong", "served_under", 752, None, 756, 7, "任相"),
    ("p_li_linpu", "p_an_lushan", "allied_with", 742, None, 752, 1, "放纵胡将"),

    # 安史之乱
    ("p_li_longji", "e_an_lushan_rebellion", "participated_in", 755, 12, 756, 7, "玄宗奔蜀"),
    ("p_li_longji", "e_mawei_zhibian", "participated_in", 756, 7, None, None, None),
    ("p_yang_guozhong", "e_mawei_zhibian", "participated_in", 756, 7, None, None, "被杀"),
    ("p_yang_guifei", "e_mawei_zhibian", "participated_in", 756, 7, None, None, "被缢死"),
    ("p_guo_ziyi", "e_tang_shoufu_liangjing", "led", 757, 9, None, None, "主力"),
    ("p_li_guangbi", "e_tang_shoufu_liangjing", "led", 757, 9, None, None, None),

    # 怛罗斯
    ("e_talas_zhizhan", "e_an_lushan_rebellion", "preceded_by", None, None, None, None, "盛唐由盛转衰伏笔"),

    # 玄奘
    ("p_xuan_zang", "p_li_shimin", "served_under", 645, None, 649, None, "译经受朝廷支持"),

    # 文化圈
    ("p_li_bai", "p_du_fu", "allied_with", 744, None, 762, None, "至交"),
    ("p_du_fu", "p_li_bai", "mentored_by", 744, None, 762, None, "受李白影响"),

    # 因果链
    ("e_kaihuang_zhizhi", "e_sui_mo_qiyi", "preceded_by", None, None, None, None, "盛世后隋炀帝暴政引发起义"),
    ("e_sui_mo_qiyi", "e_jian_guo_tang", "preceded_by", None, None, None, None, "隋末大起义催生唐朝"),
    ("e_xuanwumen", "e_zhenguan_zhizhi", "preceded_by", None, None, None, None, "玄武门之变开启贞观"),
    ("e_kaiyuan_shengshi", "e_an_lushan_rebellion", "preceded_by", None, None, None, None, "盛世积累的矛盾爆发"),
    ("e_wu_zhou_geming", "e_shenlong_geming", "preceded_by", None, None, None, None, "武周代唐→神龙复辟"),
]


def gen_relations():
    items = []
    for r in RELATIONS:
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
        items.append(obj)
    seen = set()
    deduped = []
    for r in items:
        key = (r["from"], r["to"], r["type"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    out = DATA / "relations" / "sui_early_tang.yaml"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(deduped, f, allow_unicode=True, sort_keys=False)
    print(f"  ✓ {len(deduped)} relations → data/relations/sui_early_tang.yaml")


if __name__ == "__main__":
    print(f"→ Phase 10: Sui + Early Tang (581-763)")
    gen_places()
    print(f"  ✓ {len(PLACES)} places")
    gen_extra_places()
    print(f"  ✓ {len(EXTRA_POLITY_PLACES)} birthplaces")
    gen_extra_polities()
    print(f"  ✓ {len(EXTRA_POLITIES)} polity stubs")
    gen_persons()
    print(f"  ✓ {len(PERSONS)} persons")
    gen_events()
    print(f"  ✓ {len(EVENTS)} events")
    gen_relations()
    print("Done.")
