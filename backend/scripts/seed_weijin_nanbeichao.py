#!/usr/bin/env python3
"""Phase 11 — Three Kingdoms, Two Jins, Sixteen Kingdoms, Southern & Northern Dynasties (220-589).

Coverage:
- 三国 (220-280):曹魏 / 蜀汉 / 东吴 + 关键人物
- 西晋 (266-316) + 八王之乱 + 永嘉之乱
- 东晋 (317-420) + 南朝 (宋齐梁陈)
- 十六国 (304-439)
- 北朝 (北魏→东西魏→北齐北周)
- 孝文帝汉化 / 关陇集团形成
"""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)


PLACES = [
    ("pl_luoyang_han", "洛阳", "洛阳", "河南", 34.62, 112.45, "capital", [], "汉魏晋都"),
    ("pl_xuchang", "许昌", "许昌", "河南", 34.03, 113.85, "capital", [], "曹魏后期都"),
    ("pl_yecheng", "邺城", "临漳/安阳", "河北", 36.21, 114.62, "capital", [], "魏晋北朝重镇"),
    ("pl_chengdu_han", "成都", "成都", "四川", 30.67, 104.07, "capital", [], "蜀汉都"),
    ("pl_jianye_han", "建业", "南京", "江苏", 32.04, 118.78, "capital", ["建康"], "东吴东晋南朝都"),
    ("pl_changsha_han", "长沙", "长沙", "湖南", 28.23, 112.94, "city", [], "东汉孙坚任长沙太守"),
    ("pl_chaisang", "柴桑", "九江", "江西", 29.71, 115.99, "battlefield", [], "赤壁之战周瑜驻地"),
    ("pl_chibi", "赤壁", "赤壁", "湖北", 29.73, 113.91, "battlefield", [], "208 赤壁之战"),
    ("pl_guandu", "官渡", "中牟", "河南", 34.34, 114.07, "battlefield", [], "200 官渡之战"),
    ("pl_yiling", "夷陵", "宜昌", "湖北", 30.70, 111.32, "battlefield", ["猇亭"], "222 夷陵之战"),
    ("pl_jiangling_han", "江陵", "荆州", "湖北", 30.33, 112.24, "city", [], "战略要地"),
    ("pl_xiangyang_han", "襄阳", "襄阳", "湖北", 32.04, 112.12, "city", [], "荆州要冲"),
    ("pl_hanzhong_han", "汉中", "汉中", "陕西", 33.07, 107.03, "city", [], "蜀汉北门户"),
    ("pl_qishan", "祁山", "礼县", "甘肃", 34.20, 105.13, "battlefield", [], "诸葛亮出祁山"),
    ("pl_wuzhangyuan", "五丈原", "岐山", "陕西", 34.20, 107.65, "battlefield", [], "234 诸葛亮病逝"),
    ("pl_jinling_jiankang", "建康", "南京", "江苏", 32.04, 118.78, "capital", ["金陵"], "六朝都城"),
    ("pl_pingcheng", "平城", "大同", "山西", 40.10, 113.30, "capital", [], "北魏早期都"),
    ("pl_luoyang_beiwei", "洛阳(北魏)", "洛阳", "河南", 34.62, 112.45, "capital", [], "北魏孝文帝迁都"),
    ("pl_heyin", "河阴", "孟津", "河南", 34.83, 112.46, "battlefield", [], "528 河阴之变"),
    ("pl_yedu", "邺都", "临漳", "河北", 36.21, 114.62, "capital", [], "东魏北齐都"),
    ("pl_chang_an_xiwei", "长安(西魏)", "西安", "陕西", 34.27, 108.95, "capital", [], "西魏北周都"),
    ("pl_jinzhou_beiwei", "晋阳", "太原", "山西", 37.77, 112.55, "city", [], "高欢大本营"),
    ("pl_feishui", "淝水/寿阳", "寿县", "安徽", 32.57, 116.78, "battlefield", [], "383 淝水之战"),
    ("pl_yecheng_2", "邺/尹", "临漳", "河北", 36.21, 114.62, "city", [], "冉魏前燕都"),
    ("pl_zhongshan", "中山", "定州", "河北", 38.51, 115.01, "city", [], "后燕都"),
    ("pl_longcheng", "龙城", "朝阳", "辽宁", 41.57, 120.45, "city", [], "前燕北燕"),
    ("pl_pingliang_xiliang", "姑臧/凉州", "武威", "甘肃", 37.93, 102.64, "capital", [], "前凉后凉北凉"),
    ("pl_chang_an_houzhao", "长安/襄国", "邢台/西安", "河北", 37.07, 114.50, "capital", [], "后赵"),
    ("pl_xiangguo", "襄国", "邢台", "河北", 37.07, 114.50, "capital", [], "后赵石勒"),
    ("pl_qiu_ci_xiliang", "龟兹", "库车", "新疆", 41.72, 82.95, "city", [], "鸠摩罗什来源"),
    ("pl_yongnian", "广平/易阳", "永年", "河北", 36.77, 114.50, "city", [], "六镇之一"),
    ("pl_huai_sheng_zhen", "怀朔镇", "固阳", "内蒙古", 40.95, 110.00, "garrison", [], "六镇之一"),
    ("pl_wuchuan_6zhen", "武川镇", "武川", "内蒙古", 41.10, 111.45, "garrison", [], "六镇之一,关陇集团发源"),
    ("pl_funing_6zhen", "抚冥镇", "四子王旗", "内蒙古", 41.50, 111.70, "garrison", [], "六镇之一"),
    ("pl_huaishuo_6zhen", "怀荒镇", "尚义", "河北", 41.10, 113.90, "garrison", [], "六镇之一"),
    ("pl_youzhou_sanguo", "涿郡/范阳", "涿州", "河北", 39.49, 115.98, "city", [], "刘备祖籍"),
]


def gen_places():
    for tup in PLACES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["三国志", "晋书", "宋书", "魏书", "中国历史地图集"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


PERSONS = [
    # === 东汉末 / 曹魏奠基 ===
    ("p_cao_cao", "曹操", ["曹孟德", "魏武帝", "曹吉利"], "孟德", (155, None), (220, 3), "pl_qiao_cao",
     "东汉末年杰出的政治家、军事家、文学家。沛国谯县人。189 起兵讨董卓,196 迎汉献帝都许,'挟天子以令诸侯'。200 官渡之战大破袁绍,统一北方。208 赤壁之战败北,三国鼎立成。213 魏公,216 魏王。220 病卒,子丕代汉。",
     "中国历史最具争议的人物之一。建安文学领袖。",
     ["三国志·魏书·武帝纪", "资治通鉴·卷60-68"]),
    ("p_cao_pi", "曹丕", ["曹子桓", "魏文帝"], "子桓", (187, None), (226, 6), "pl_qiao_cao",
     "曹魏建立者。曹操次子。220 即魏王位,十月迫汉献帝禅让,国号魏,都洛阳。在位 7 年。",
     ["三国志·魏书·文帝纪"]),
    ("p_cao_rui", "曹叡", ["曹元仲", "魏明帝"], "元仲", (205, None), (239, 1), "pl_luoyang_han",
     "曹魏第二任皇帝。226-239 在位。抵御诸葛亮北伐。",
     ["三国志·魏书·明帝纪"]),
    ("p_caocao_sons", "曹植", ["曹子建", "陈思王"], "子建", (192, None), (232, 12), "pl_qiao_cao",
     "曹操子,曹丕弟。建安文学代表。'七步成诗'。",
     ["三国志·魏书·陈思王传"]),
    ("p_caocao_sons_2", "曹彰", ["曹子文"], "子文", (None, None), (223, None), "pl_qiao_cao",
     "曹操子。骁勇。'黄须儿'。",
     ["三国志·魏书·任城威王彰传"]) if False else
    ("p_cao_zhang", "曹彰", ["曹子文"], "子文", (None, None), (223, None), "pl_qiao_cao",
     "曹操子。骁勇。'黄须儿'。",
     ["三国志·魏书·任城威王彰传"]),
    ("p_cao_chong", "曹冲", ["曹仓舒"], None, (196, None), (208, None), "pl_qiao_cao",
     "曹操子。'曹冲称象'。早慧,13 岁夭折。",
     ["三国志·魏书·邓哀王冲传"]),
    ("p_xun_yu", "荀彧", ["荀文若"], "文若", (163, None), (212, None), "pl_yingchuan_xunyu",
     "曹操首席谋士。颍川颍阴人。'王佐之才'。196 劝曹操迎献帝都许。212 因反对曹操进魏公,被迫自杀。",
     ["三国志·魏书·荀彧传"]),
    ("p_xun_you", "荀攸", ["荀公达"], "公达", (157, None), (214, None), "pl_yingchuan_xunyu",
     "曹操谋士。荀彧侄。",
     ["三国志·魏书·荀攸传"]),
    ("p_guo_jia", "郭嘉", ["郭奉孝"], "奉孝", (170, None), (207, None), "pl_yangzhai_guojia",
     "曹操谋士。颍川阳翟人。'十胜十败'论。207 病卒于征乌丸途中。",
     ["三国志·魏书·郭嘉传"]),
    ("p_jia_xu", "贾诩", ["贾文和"], "文和", (147, None), (223, None), "pl_weiyuan_jiaxu",
     "曹操谋士。原董卓、张绣部下。'算无遗策'。",
     ["三国志·魏书·贾诩传"]),
    ("p_simayi", "司马懿", ["司马仲达", "晋宣帝"], "仲达", (179, None), (251, 9), "pl_wen_xianyu",
     "曹魏权臣。河内温县人。历仕曹操、丕、叡、芳四代。249 高平陵之变诛曹爽,掌握魏国大权。子师、昭继之,孙炎代魏建晋。",
     "晋朝奠基者。",
     ["三国志·魏书·司马懿传", "晋书·宣帝纪"]),
    ("p_xiahou_dun", "夏侯惇", ["夏侯元让"], "元让", (None, None), (220, 6), "pl_qiao_cao",
     "曹魏宗将。'盲夏侯'。",
     ["三国志·魏书·夏侯惇传"]),
    ("p_xiahou_yuan", "夏侯渊", ["夏侯妙才"], "妙才", (None, None), (219, None), "pl_qiao_cao",
     "曹魏宗将。219 定军山为黄忠所杀。",
     ["三国志·魏书·夏侯渊传"]),
    ("p_zhang_liao", "张辽", ["张文远"], "文远", (169, None), (222, None), "pl_mayi_zhangliao",
     "曹魏骁将。原吕布部下。215 逍遥津大破孙权。",
     ["三国志·魏书·张辽传"]),
    ("p_xu_huang", "徐晃", ["徐公明"], "公明", (None, None), (227, None), "pl_yangping_xuhuang",
     "曹魏骁将。219 破关羽于樊城。",
     ["三国志·魏书·徐晃传"]),

    # === 蜀汉 ===
    ("p_liu_bei", "刘备", ["刘玄德", "刘先主", "汉昭烈帝"], "玄德", (161, None), (223, 4), "pl_youzhou_sanguo",
     "蜀汉建立者。涿郡涿县人。汉中山靖王之后(自称)。早年颠沛。207 三顾茅庐,得诸葛亮。208 赤壁之战后据荆州。214 取益州。219 取汉中,自立汉中王。221 称帝,国号汉(蜀),都成都。222 夷陵之战大败于陆逊。223 病卒于白帝城,托孤诸葛亮。",
     "三国时代最传奇的开国者。",
     ["三国志·蜀书·先主传", "资治通鉴·卷60-70"]),
    ("p_zhuge_liang", "诸葛亮", ["诸葛孔明", "卧龙", "诸葛武侯"], "孔明", (181, None), (234, 8), "pl_yangdu_zhuge",
     "蜀汉丞相。琅琊阳都人。207 三顾后出山。'隆中对'。221 任丞相。223 受托孤。225 平南中(七擒孟获)。227-234 五次北伐曹魏。234 病逝于五丈原。'鞠躬尽瘁,死而后已'。",
     "中国历史上忠臣与智慧的化身。",
     ["三国志·蜀书·诸葛亮传", "资治通鉴·卷65-72"]),
    ("p_guan_yu", "关羽", ["关云长", "关公"], "云长", (None, None), (220, 1), "pl_xie_xianguanyu",
     "蜀汉骁将。河东解良人。桃园结义(演义)。200 斩颜良。219 水淹七军,擒于禁斩庞德,威震华夏。后为吕蒙偷袭,败走麦城被杀。",
     "中国武勇与忠义的象征,后世封'关圣帝君'。",
     ["三国志·蜀书·关羽传"]),
    ("p_zhang_fei", "张飞", ["张翼德"], "翼德", (None, None), (221, None), "pl_zhuo_zhangfei",
     "蜀汉骁将。涿郡人。当阳桥喝断,义释严颜。221 为部下所杀。",
     ["三国志·蜀书·张飞传"]),
    ("p_zhao_yun", "赵云", ["赵子龙"], "子龙", (None, None), (229, None), "pl_zhending_zhaoyun",
     "蜀汉骁将。常山真定人。长坂坡救阿斗。",
     ["三国志·蜀书·赵云传"]),
    ("p_ma_chao", "马超", ["马孟起"], "孟起", (176, None), (222, None), "pl_maying_machao",
     "蜀汉骁将。扶风茂陵人。父马腾。凉州军阀。215 投刘备。",
     ["三国志·蜀书·马超传"]),
    ("p_huang_zhong", "黄忠", ["黄汉升"], "汉升", (None, None), (220, None), "pl_nanyang_huangzhong",
     "蜀汉骁将。219 定军山斩夏侯渊。",
     ["三国志·蜀书·黄忠传"]),
    ("p_wei_yan", "魏延", ["魏文长"], "文长", (None, None), (234, None), "pl_yiyang_weiyan",
     "蜀汉骁将。234 诸葛亮死后因与杨仪不和,被诬谋反,诛。",
     ["三国志·蜀书·魏延传"]),
    ("p_jiang_wei", "姜维", ["姜伯约"], "伯约", (202, None), (264, None), "pl_jixian_jiangwei",
     "蜀汉后期大将。天水冀县人。诸葛亮传人。247-262 九伐中原。263 蜀亡,降钟会后图谋反叛复国,失败被杀。",
     ["三国志·蜀书·姜维传"]),
    ("p_liu_shan", "刘禅", ["阿斗", "后主"], None, (207, None), (271, None), "pl_chengdu_han",
     "蜀汉后主。刘备子。223-263 在位。诸葛亮辅政。263 魏将邓艾入成都,降。'乐不思蜀'。",
     ["三国志·蜀书·后主传"]),

    # === 东吴 ===
    ("p_sun_jian", "孙坚", ["孙文台"], "文台", (155, None), (192, None), "pl_fuchun_sunjian",
     "东吴奠基者。吴郡富春人。长沙太守。192 攻刘表部将黄祖,中伏死。",
     ["三国志·吴书·孙坚传"]),
    ("p_sun_ce", "孙策", ["孙伯符", "小霸王"], "伯符", (175, None), (200, 4), "pl_fuchun_sunjian",
     "东吴奠基者。孙坚子。194-200 平定江东。200 为刺客所伤卒,弟权继。",
     ["三国志·吴书·孙策传"]),
    ("p_sun_quan", "孙权", ["孙仲谋", "吴大帝"], "仲谋", (182, None), (252, 4), "pl_fuchun_sunjian",
     "东吴建立者。孙策弟。200 继兄位。208 联刘备破曹操于赤壁。219 取荆州,杀关羽。222 称吴王,229 称帝,都建业。252 病卒。",
     ["三国志·吴书·吴主传", "资治通鉴·卷63-75"]),
    ("p_zhou_yu", "周瑜", ["周公瑾"], "公瑾", (175, None), (210, 12), "pl_shu_yang_zhouyu",
     "东吴名将。庐江舒县人。208 赤壁之战主帅,大破曹操。210 病逝于巴丘,年 36。",
     "中国军事史经典战例统帅。",
     ["三国志·吴书·周瑜传"]),
    ("p_lu_su", "鲁肃", ["鲁子敬"], "子敬", (172, None), (217, None), "pl_dongcheng_lusu",
     "东吴谋士。210 劝孙权借荆州与刘备。'榻上策'。",
     ["三国志·吴书·鲁肃传"]),
    ("p_lv_meng", "吕蒙", ["吕子明"], "子明", (178, None), (220, None), "pl_fupo_lvmeng",
     "东吴名将。219 白衣渡江,擒关羽。'士别三日,当刮目相待'。",
     ["三国志·吴书·吕蒙传"]),
    ("p_lu_xun", "陆逊", ["陆伯言"], "伯言", (183, None), (245, None), "pl_wu_xian_luxun",
     "东吴名将。222 夷陵之战火烧连营,大破刘备。后任丞相。",
     ["三国志·吴书·陆逊传"]),

    # === 西晋 ===
    ("p_simayan", "司马炎", ["晋武帝", "司马安世"], "安世", (236, None), (290, 5), "pl_wen_xianyu",
     "西晋建立者。司马昭子。265 代魏建晋,都洛阳。280 灭吴统一中国。290 病卒。'平吴之后怠政'。",
     "结束三国分裂,但西晋短暂统一即崩溃。",
     ["晋书·武帝纪", "资治通鉴·卷79-82"]),
    ("p_sima_zhao", "司马昭", ["司马子上", "晋文帝"], "子上", (211, None), (265, 9), "pl_wen_xianyu",
     "司马师弟。兄死继大将军。263 灭蜀。265 病卒,子炎代魏建晋。",
     ["晋书·文帝纪"]),
    ("p_sima_shi", "司马师", ["司马子元", "晋景帝"], "子元", (208, None), (255, 3), "pl_wen_xianyu",
     "司马懿长子。251 继父执政。254 废魏帝曹芳。255 病卒。",
     ["晋书·景帝纪"]),
    ("p_simazhong", "司马衷", ["晋惠帝"], None, (259, None), (307, 1), "pl_luoyang_han",
     "西晋第二任皇帝。武帝子。'何不食肉糜'者。290-307 在位。291-306 八王之乱。307 食饼中毒卒(传)。",
     ["晋书·惠帝纪"]),
    ("p_jia_nan_feng", "贾南风", ["贾皇后", "贾南风"], None, (257, None), (300, 5), "pl_xiangling_jiananfeng",
     "晋惠帝皇后。貌丑而权欲强。291 起八王之乱,废杀杨太后、太子遹。300 为赵王司马伦所杀。",
     "八王之乱的直接祸首。",
     ["晋书·后妃传·贾南风"]),
    ("p_wang_dao", "王导", ["王茂弘"], "茂弘", (276, None), (339, None), "pl_linyi_wangdao",
     "东晋开国元勋。琅琊临沂人。317 与从兄王敦辅司马睿建东晋。'王与马,共天下'。",
     ["晋书·王导传"]),
    ("p_xie_an", "谢安", ["谢安石"], "安石", (320, None), (385, 10), "pl_yangxia_xiean",
     "东晋政治家。陈郡阳夏人。383 淝水之战主帅,大破前秦苻坚。",
     ["晋书·谢安传"]),

    # === 十六国核心 ===
    ("p_liu_yuan", "刘渊", ["刘元海", "汉赵高祖"], "元海", (None, None), (310, 8), "pl_zuo_han_liuyuan",
     "汉赵(前赵)建立者。匈奴屠各种。304 称汉王,308 称帝,都平阳(山西临汾)。308-310 在位。开启十六国时代。",
     "五胡十六国之始。",
     ["晋书·载记·刘元海"]),
    ("p_shi_le", "石勒", ["石世龙", "后赵高祖"], None, (274, None), (333, 7), "pl_wuxiang_shile",
     "后赵建立者。羯族。319 称赵王,都襄国。329 灭前赵。330 称帝。奴隶出身的开国者。",
     ["晋书·载记·石勒", "魏书·羯胡传"]),
    ("p_fu_jian", "苻坚", ["苻永固", "前秦宣昭帝", "苻坚"], "永固", (338, None), (385, 10), "pl_lintong_fujian",
     "前秦君主。氐族。357-385 在位。370 灭前燕,376 灭前凉、代,统一北方。383 淝水之战大败,帝国崩溃。385 为姚苌所缢。",
     "383 之前北方最接近统一的君主。",
     ["晋书·载记·苻坚", "资治通鉴·卷102-105"]),

    # === 南朝(宋齐梁陈) ===
    ("p_liu_yu", "刘裕", ["刘德舆", "宋武帝", "刘寄奴"], "德舆", (363, None), (422, 6), "pl_pengcheng_liuyu",
     "南朝宋建立者。彭城人,生于京口。北府兵出身。402 破桓玄。409-410 灭南燕。417 灭后秦,收复洛阳、长安。420 代晋建宋。'气吞万里如虎'。",
     "南朝最杰出的君主。",
     ["宋书·武帝纪", "资治通鉴·卷113-119"]),
    ("p_xiao_yan", "萧衍", ["梁武帝", "叔达"], "叔达", (464, None), (549, 5), "pl_nanlanxia_xiaoyan",
     "南朝梁建立者。502-549 在位。在位 48 年,前期'天监之治'。548-549 侯景之乱,被围台城饿死。奉佛,数度舍身同泰寺。",
     ["梁书·武帝纪", "资治通鉴·卷144-162"]),
    ("p_hou_jing", "侯景", None, None, (503, None), (552, None), "pl_huaixian_houjing",
     "朔方人,羯族。原东魏将领,547 叛降梁。548 起兵围台城,549 破之,萧衍饿死。551 自立为帝,国号汉。552 为陈霸先、王僧辩所破,被部下所杀。",
     "南朝转折性事件,江南经济文化大破坏。",
     ["梁书·侯景传", "南史·贼臣传"]),
    ("p_chen_baxian", "陈霸先", ["陈兴国", "陈武帝"], "兴国", (503, None), (559, 8), "pl_changcheng_chenbaxian",
     "南朝陈建立者。吴兴长城人。552 平侯景之乱。557 代梁建陈。都建康。",
     ["陈书·武帝纪"]),
    ("p_chen_shubao", "陈叔宝", ["陈后主"], None, (553, None), (604, None), "pl_changcheng_chenbaxian",
     "南朝陈末代君主。582-589 在位。荒淫词人。589 隋军破建康,跳井躲藏被俘。'商女不知亡国恨'。",
     ["陈书·后主纪"]),

    # === 北朝 ===
    ("p_tuoba_gui", "拓跋珪", ["魏道武帝"], None, (371, None), (409, None), "pl_sheng_le_tuobagui",
     "北魏建立者。鲜卑拓跋部。386 复国代,改国号魏。398 都平城(大同)。",
     ["魏书·太祖纪", "北史·魏本纪"]),
    ("p_tuoba_hong", "拓跋宏", ["元宏", "魏孝文帝"], None, (467, None), (499, 4), "pl_pingcheng",
     "北魏孝文帝。471-499 在位。493-494 自平城迁都洛阳,改姓元,推行汉化:穿汉服、说汉语、与汉人通婚、用汉制。498 病卒于南征途中。",
     "中国民族融合史上的关键人物。",
     ["魏书·高祖纪", "资治通鉴·卷138-142"]),
    ("p_er_zhu_rong", "尔朱荣", None, None, (493, None), (530, 9), "pl_xiurong_erzhurong",
     "北魏末权臣。契胡族。528 胡太后毒杀孝明帝,尔朱荣起兵入洛阳,立孝庄帝,在河阴屠杀百官二千余(河阴之变)。530 为孝庄帝诱杀。",
     "北魏分裂的导火索。",
     ["魏书·尔朱荣传", "资治通鉴·卷152-154"]),
    ("p_gao_huan", "高欢", ["贺六浑"], None, (496, None), (547, 2), "pl_hejian_gaohuan",
     "东魏实际建立者。渤海蓨人,生于怀朔镇(六镇之一)。532 入洛阳立孝武帝,534 孝武帝西奔,欢另立孝静帝,迁都邺,东魏始。547 病卒。子洋代魏建北齐。",
     ["北齐书·神武纪", "魏书·献武王传"]),
    ("p_yuwen_tai_pre", "宇文泰(已存在标记)", None, None, (None, None), (None, None), None,
     "已存在", []) if False else None,

    # === 关陇集团核心(补充更多八柱国)===
    ("p_yuan_baoju", "元宝炬", ["西魏文帝"], None, (507, None), (551, 3), "pl_luoyang_beiwei",
     "西魏建立者。北魏孝文帝孙。534 与高欢决裂,西奔长安依宇文泰,被立为帝,西魏始。在位 17 年。",
     ["周书·文帝纪"]),
    ("p_yuwen_jue", "宇文觉", ["北周孝闵帝"], None, (542, None), (557, None), "pl_chang_an_xiwei",
     "北周建立者。宇文泰子。557 代西魏建周,称天王。同年为堂兄宇文护所废杀。",
     ["周书·孝闵帝纪"]),
    ("p_yuwen_yong", "宇文邕", ["北周武帝"], None, (543, None), (578, 6), "pl_chang_an_xiwei",
     "北周武帝。560-578 在位。572 杀权臣宇文护亲政。574 灭佛(三武一宗之二)。577 灭北齐,统一北方。578 病卒于征突厥途中。",
     "为杨坚统一中国奠定基础。",
     ["周书·武帝纪", "资治通鉴·卷171-173"]),
    ("p_yang_jian_pre", "杨坚(已存在)", None, None, (None, None), (None, None), None, "", []) if False else None,
]
PERSONS = [p for p in PERSONS if p is not None and not p[0].endswith(("_existing", "_add", "_pre"))]


# Extra birthplaces
EXTRA_PLACES_BIRTH = [
    ("pl_qiao_cao", "谯", "亳州", "安徽", 33.85, 115.78, "birthplace", [], "曹操籍贯"),
    ("pl_yingchuan_xunyu", "颍阴", "许昌", "河南", 34.03, 113.85, "birthplace", [], "荀彧籍贯"),
    ("pl_yangzhai_guojia", "阳翟", "禹州", "河南", 34.16, 113.47, "birthplace", [], "郭嘉籍贯"),
    ("pl_weiyuan_jiaxu", "武威/姑臧", "武威", "甘肃", 37.93, 102.64, "birthplace", [], "贾诩籍贯"),
    ("pl_wen_xianyu", "温县", "温县", "河南", 34.95, 113.07, "birthplace", [], "司马懿籍贯"),
    ("pl_mayi_zhangliao", "马邑", "朔州", "山西", 39.32, 112.43, "birthplace", [], "张辽籍贯"),
    ("pl_yangping_xuhuang", "阳平/杨县", "洪洞", "山西", 36.41, 111.71, "birthplace", [], "徐晃籍贯"),
    ("pl_xie_xianguanyu", "解良", "运城", "山西", 35.03, 111.05, "birthplace", [], "关羽籍贯"),
    ("pl_zhuo_zhangfei", "涿郡", "涿州", "河北", 39.49, 115.98, "birthplace", [], "张飞籍贯"),
    ("pl_zhending_zhaoyun", "常山真定", "正定", "河北", 38.15, 114.57, "birthplace", [], "赵云籍贯"),
    ("pl_maying_machao", "茂陵/扶风", "兴平", "陕西", 34.30, 108.49, "birthplace", [], "马超籍贯"),
    ("pl_nanyang_huangzhong", "南阳", "南阳", "河南", 32.99, 112.53, "birthplace", [], "黄忠籍贯"),
    ("pl_yiyang_weiyan", "义阳", "信阳", "河南", 32.13, 114.07, "birthplace", [], "魏延籍贯"),
    ("pl_jixian_jiangwei", "冀县", "甘谷", "甘肃", 34.75, 105.34, "birthplace", [], "姜维籍贯"),
    ("pl_fuchun_sunjian", "富春", "富阳", "浙江", 30.05, 119.95, "birthplace", [], "孙坚籍贯"),
    ("pl_shu_yang_zhouyu", "舒县", "庐江", "安徽", 31.26, 117.29, "birthplace", [], "周瑜籍贯"),
    ("pl_dongcheng_lusu", "东城", "定远", "安徽", 32.53, 117.68, "birthplace", [], "鲁肃籍贯"),
    ("pl_fupo_lvmeng", "阜坡/汝南", "平舆", "河南", 33.00, 114.69, "birthplace", [], "吕蒙籍贯"),
    ("pl_wu_xian_luxun", "吴郡/华亭", "苏州", "江苏", 31.30, 120.62, "birthplace", [], "陆逊籍贯"),
    ("pl_yangdu_zhuge", "阳都", "沂南", "山东", 35.55, 118.47, "birthplace", [], "诸葛亮籍贯"),
    ("pl_xiangling_jiananfeng", "襄陵", "襄汾", "山西", 35.87, 111.45, "birthplace", [], "贾南风籍贯"),
    ("pl_linyi_wangdao", "临沂", "临沂", "山东", 35.10, 118.35, "birthplace", [], "王导籍贯"),
    ("pl_yangxia_xiean", "阳夏/太康", "太康", "河南", 34.07, 114.85, "birthplace", [], "谢安籍贯"),
    ("pl_zuo_han_liuyuan", "左国城/新兴", "离石", "山西", 37.52, 111.15, "birthplace", [], "刘渊起兵地"),
    ("pl_wuxiang_shile", "武乡", "武乡", "山西", 36.95, 112.84, "birthplace", [], "石勒籍贯"),
    ("pl_lintong_fujian", "临潼/邺", "临潼", "陕西", 34.37, 109.21, "birthplace", [], "苻坚相关"),
    ("pl_pengcheng_liuyu", "彭城", "徐州", "江苏", 34.26, 117.18, "birthplace", [], "刘裕籍贯"),
    ("pl_nanlanxia_xiaoyan", "南兰陵", "武进", "江苏", 31.71, 119.97, "birthplace", [], "萧衍籍贯"),
    ("pl_huaixian_houjing", "怀朔镇", "固阳", "内蒙古", 40.95, 110.00, "birthplace", [], "侯景籍贯"),
    ("pl_changcheng_chenbaxian", "长城", "长兴", "浙江", 31.01, 119.91, "birthplace", [], "陈霸先籍贯"),
    ("pl_sheng_le_tuobagui", "盛乐", "和林格尔", "内蒙古", 40.41, 111.81, "birthplace", [], "拓跋珪早期都"),
    ("pl_hejian_gaohuan", "渤海蓨", "景县", "河北", 37.69, 116.27, "birthplace", [], "高欢祖籍"),
    ("pl_xiurong_erzhurong", "秀容", "忻州", "山西", 38.42, 112.73, "birthplace", [], "尔朱荣籍贯"),
]


def gen_persons():
    for tup in PERSONS:
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
        if pid in ("p_jia_nan_feng",):
            obj["gender"] = "female"
        if birthplace:
            obj["birthplace"] = birthplace
        obj["bio"] = bio
        if significance:
            obj["ext"] = {"significance": significance}
        obj["sources"] = srcs
        write(DATA / "entities" / "persons" / f"{pid[2:]}.yaml", obj)


def gen_birthplaces():
    for tup in EXTRA_PLACES_BIRTH:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["三国志", "晋书", "魏书", "中国历史地图集"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# Polities for the era
POLITIES = [
    ("k_caowei", "曹魏", "Cao Wei", "#c0392b", (220, 12), (266, 2), "p_caopi", "pl_luoyang_han", "d_donghan", "k_xijin",
     "三国之一。曹丕代汉建。司马氏渐夺权,266 为西晋所代。",
     "三国志·魏书;晋书"),
    ("k_shuhan", "蜀汉", "Shu Han", "#27ae60", (221, 4), (263, 11), "p_liu_bei", "pl_chengdu_han", None, "k_caowei",
     "三国之一。刘备建,都成都。263 为魏将邓艾所灭。",
     "三国志·蜀书"),
    ("k_dongwu", "东吴", "Eastern Wu", "#3498db", (222, None), (280, 3), "p_sun_quan", "pl_jianye_han", None, "k_xijin",
     "三国之一。孙权建,都建业。280 为西晋所灭。",
     "三国志·吴书"),
    ("k_xijin", "西晋", "Western Jin", "#16a085", (266, 2), (316, 12), "p_simayan", "pl_luoyang_han", "k_caowei", "k_dongjin_pre",
     "司马炎代魏建。280 灭吴统一。316 亡于汉赵(永嘉之乱)。",
     "晋书·武帝纪"),
    ("k_dongjin", "东晋", "Eastern Jin", "#9b59b6", (317, 3), (420, 7), None, "pl_jianye_han", "k_xijin", "k_liusong",
     "东晋。317 司马睿在建康称晋王,318 称帝。偏安江南。420 为刘裕所代。",
     "晋书·元帝纪"),
    ("k_liusong", "刘宋", "Liu Song", "#8e44ad", (420, 7), (479, 4), "p_liu_yu", "pl_jianye_han", "k_dongjin", "k_nan_qi",
     "南朝宋。刘裕建。",
     "宋书"),
    ("k_nan_qi", "南齐", "Southern Qi", "#34495e", (479, 4), (502, 4), None, "pl_jianye_han", "k_liusong", "k_nan_liang",
     "南朝齐。萧道成建。",
     "南齐书"),
    ("k_nan_liang", "梁", "Liang", "#c0392b", (502, 4), (557, 10), "p_xiao_yan", "pl_jianye_han", "k_nan_qi", "k_nan_chen",
     "南朝梁。萧衍建。'天监之治'。侯景之乱后衰落。",
     "梁书"),
    ("k_nan_chen", "陈", "Chen", "#f1c40f", (557, 10), (589, 1), "p_chen_baxian", "pl_jianye_han", "k_nan_liang", "d_sui",
     "南朝陈。陈霸先建。589 为隋所灭,中国重新统一。",
     "陈书"),
    ("k_hanzhao", "汉赵/前赵", "Han-Zhao", "#7f8c8d", (304, 10), (329, None), "p_liu_yuan", "pl_zuo_han_liuyuan", None, "k_houzhao",
     "十六国之一。匈奴。304 刘渊建国,318 分裂为前赵、后赵。329 后赵灭前赵。",
     "晋书·载记"),
    ("k_houzhao", "后赵", "Later Zhao", "#95a5a6", (319, 11), (351, None), "p_shi_le", "pl_xiangguo", None, "k_ranwei_pre",
     "十六国之一。羯。石勒建。333 石虎继位,暴虐。350 冉闵灭之。",
     "晋书·载记"),
    ("k_qian_qin", "前秦", "Former Qin", "#d35400", (350, None), (394, None), None, "pl_chang_an_houzhao", None, "k_hou_qin_pre",
     "十六国之一。氐族。苻健建。苻坚朝统一北方。383 淝水之战大败,帝国崩溃。",
     "晋书·载记·苻坚"),
    ("k_beiwei", "北魏", "Northern Wei", "#1abc9c", (386, 3), (534, None), "p_tuoba_gui", "pl_pingcheng", None, "k_dong_wei",
     "北朝之一。鲜卑拓跋部建。398 都平城,494 迁洛阳。534 分裂为东西魏。",
     "魏书;北史"),
    ("k_dong_wei", "东魏", "Eastern Wei", "#16a085", (534, 10), (550, 5), None, "pl_yedu", "k_beiwei", "k_bei_qi",
     "高欢拥立。550 高洋代之建北齐。",
     "魏书;北齐书"),
    ("k_xi_wei", "西魏", "Western Wei", "#27ae60", (535, None), (557, None), "p_yuwen_tai_pre", "pl_chang_an_xiwei", "k_beiwei", "k_bei_zhou",
     "宇文泰拥立。557 宇文觉代之建北周。",
     "周书"),
    ("k_bei_qi", "北齐", "Northern Qi", "#e74c3c", (550, 5), (577, None), None, "pl_yedu", "k_dong_wei", "k_bei_zhou",
     "高洋代东魏建。北朝暴虐之最。577 为北周所灭。",
     "北齐书"),
    ("k_bei_zhou", "北周", "Northern Zhou", "#9b59b6", (557, 1), (581, 2), "p_yuwen_jue", "pl_chang_an_xiwei", "k_xi_wei", "d_sui",
     "宇文觉代西魏建。577 灭北齐统一北方。581 为杨坚所代。",
     "周书;北史"),
]


def gen_polities():
    for tup in POLITIES:
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


# Events
EVENTS = [
    ("e_huangjin_qiyi", "黄巾起义", (184, 3), (205, None), "institution", "pl_julu_sui",
     ["d_donghan"],
     "184 年二月张角率太平道信徒于冀州起兵,众数十万。汉廷令各地豪强募兵镇压。204 张角死,起义失败,但开启了群雄割据。",
     "东汉末年大起义,直接导致汉末群雄割据。",
     ["后汉书·皇甫嵩传", "资治通鉴·卷58"]),
    ("e_dong_zhuo_luan_zheng", "董卓乱政", (189, 8), None, "coup", "pl_luoyang_han",
     ["d_donghan"],
     "189 年汉灵帝崩,大将军何进召董卓入京诛宦官。董卓废少帝,立献帝,自任太师,残暴。190 各地诸侯联合讨董,卓挟献帝迁都长安,焚洛阳。",
     "汉末军阀混战开始。",
     ["后汉书·董卓传", "三国志·魏书·董卓传"]),
    ("e_guandu_zhizhan", "官渡之战", (200, 2), None, "battle", "pl_guandu",
     ["k_caowei_pre", "k_yuanshao_pre"],
     "200 年二月袁绍率 11 万南下攻曹操。曹操以 2 万守官渡。十月许攸来降,曹操夜袭乌巢烧绍粮,绍军大溃。绍仅 800 骑北逃。",
     "曹操统一北方的决定性战役。",
     ["三国志·魏书·武帝纪", "资治通鉴·卷63"]),
    ("e_chibi_zhizhan", "赤壁之战", (208, 12), None, "battle", "pl_chibi",
     ["k_caowei_pre", "k_shuhan_pre", "k_dongwu_pre"],
     "208 年曹操南下,刘备、孙权联军抗曹。周瑜为东吴主帅,以 5 万联军大破曹军 20 余万。曹操北撤,三国鼎立局面形成。",
     "中国历史上以少胜多的经典战例,决定三国鼎立。",
     ["三国志·吴书·周瑜传", "资治通鉴·卷65"]),
    ("e_yiling_zhizhan", "夷陵之战", (222, 8), None, "battle", "pl_yiling",
     ["k_shuhan", "k_dongwu"],
     "222 年刘备率 5 万攻吴,为关羽报仇、夺荆州。陆逊为吴都督,以逸待劳,火烧连营,刘备大败。223 刘备病卒于白帝城。",
     "三国鼎立最后定型。",
     ["三国志·蜀书·先主传", "资治通鉴·卷69"]),
    ("e_qishan_beifa", "诸葛亮北伐", (227, 3), (234, 8), "institution", "pl_qishan",
     ["k_shuhan", "k_caowei"],
     "227-234 年诸葛亮五次北伐曹魏。228 街亭之败(马谡)。234 五丈原,病逝。'鞠躬尽瘁,死而后已'。",
     "蜀汉后期国策。耗损蜀国国力,但延缓曹魏灭蜀。",
     ["三国志·蜀书·诸葛亮传"]),
    ("e_sijima_dai_wei", "司马氏代魏", (249, 2), (266, 2), "coup", "pl_luoyang_han",
     ["k_caowei", "k_xijin"],
     "249 年高平陵之变,司马懿诛曹爽。254-260 司马师、昭继续掌权。260 司马昭弑魏帝曹髦(成济刺之)。265 司马炎即晋王位,266 二月代魏建晋。",
     ["晋书·宣帝纪、文帝纪、武帝纪"]),
    ("e_bawang_zhiluan", "八王之乱", (291, 3), (306, None), "coup", "pl_luoyang_han",
     ["k_xijin"],
     "291-306 年西晋皇族八王争夺权力的混战。贾后废杀杨太后、太子遹引发。八王:汝南王亮、楚王玮、赵王伦、齐王冏、长沙王乂、成都王颖、河间王颙、东海王越。东海王越最终胜出。",
     "西晋元气大伤,直接导致永嘉之乱和西晋灭亡,中国陷入 270 余年分裂。",
     ["晋书·八王传", "资治通鉴·卷82-86"]),
    ("e_yongjia_zhiluan", "永嘉之乱", (311, 6), None, "coup", "pl_luoyang_han",
     ["k_xijin", "k_hanzhao"],
     "311 年汉赵刘聪、王弥、石勒攻陷洛阳,俘晋怀帝,杀王公士民三万。313 怀帝被杀,愍帝即位长安。316 长安陷,西晋亡。",
     "中国北方进入五胡十六国时代。",
     ["晋书·怀帝纪、愍帝纪", "资治通鉴·卷87"]),
    ("e_yiguan_nandu", "衣冠南渡", (317, 3), None, "diplomacy", "pl_jianye_han",
     ["k_xijin", "k_dongjin"],
     "317 年司马睿在王导辅佐下,于建康称晋王,318 称帝,东晋建立。中原士族大批南迁(衣冠南渡)。",
     "江南开发的关键转折,中国政治经济文化重心开始南移。",
     ["晋书·元帝纪"]),
    ("e_feishui_zhizhan", "淝水之战", (383, 11), None, "battle", "pl_feishui",
     ["k_dongjin", "k_qian_qin"],
     "383 年前秦苻坚率 87 万大军南下,声称'投鞭断流'。东晋谢安为总指挥,谢石、谢玄率 8 万北府兵迎战。十一月淝水之战,秦军大溃,苻坚败归。'风声鹤唳,草木皆兵'。",
     "中国历史上以少胜多的经典战例。东晋延续,前秦崩溃,北方再度分裂。",
     ["晋书·谢玄传、苻坚载记", "资治通鉴·卷105"]),
    ("e_houjing_zhiluan", "侯景之乱", (548, 8), (552, None), "institution", "pl_jianye_han",
     ["k_nan_liang"],
     "548 年东魏降将侯景叛梁,渡江围台城。549 三月城破,梁武帝萧衍饿死。江南文化经济大破坏。552 王僧辩、陈霸先平之。",
     "南朝转折点,江南大衰落。",
     ["梁书·侯景传", "南史·贼臣传"]),
    ("e_xiaowendi_hanhua", "孝文帝汉化", (494, None), None, "reform", "pl_luoyang_beiwei",
     ["k_beiwei"],
     "494 年北魏孝文帝自平城迁都洛阳,推行全面汉化:改姓元(改拓跋为元)、禁胡服胡语、与汉人通婚、用汉制。",
     "中国民族融合史上的标志性事件,影响隋唐政治格局。",
     ["魏书·高祖纪", "资治通鉴·卷139-141"]),
    ("e_liuzhen_zhiluan", "六镇之乱", (523, None), (525, None), "institution", "pl_wuchuan_6zhen",
     ["k_beiwei"],
     "523-525 年北魏北方六镇(沃野、怀朔、武川、抚冥、柔玄、怀荒)军户起义。被尔朱荣镇压。但六镇武人集团从此走上政治舞台。",
     "孕育了关陇集团(宇文泰)和高欢集团,直接导致北魏分裂。",
     ["魏书·肃宗纪", "北史·魏本纪"]),
    ("e_heyin_zhibian", "河阴之变", (528, 4), None, "coup", "pl_heyin",
     ["k_beiwei"],
     "528 年尔朱荣借口胡太后毒杀孝明帝,率军入洛阳,在河阴(河南孟津)屠百官公卿二千余人,胡太后与幼主沉于黄河。立孝庄帝。",
     "北魏分裂的导火索。",
     ["魏书·尔朱荣传", "资治通鉴·卷152"]),
    ("e_beiwei_fenlie", "北魏分裂", (534, None), None, "coup", "pl_yedu",
     ["k_beiwei", "k_dong_wei", "k_xi_wei"],
     "534 年高欢拥立孝静帝迁都邺,东魏;宇文泰拥立文帝都长安,西魏。北魏分裂。",
     "北朝进入东西对立,演化为北齐(高欢子)vs 北周(宇文泰子)。",
     ["魏书·孝静纪", "周书·文帝纪"]),
    ("e_beizhou_mie_beiqi", "北周灭北齐", (577, None), None, "institution", "pl_yedu",
     ["k_bei_zhou", "k_bei_qi"],
     "577 年北周武帝宇文邕率军攻邺,北齐后主高纬被俘,北齐亡。北方统一。",
     "为杨坚代周建隋、隋统一全国奠定基础。",
     ["周书·武帝纪", "北齐书·后主纪"]),
]


def gen_events():
    for tup in EVENTS:
        if len(tup) == 9:
            eid, name, date, end, category, place, polities, desc, srcs = tup
            impact = None
        else:
            eid, name, date, end, category, place, polities, desc, impact, srcs = tup
        obj = {
            "id": eid, "type": "Event", "name": name,
            "date": {"year": date[0]} if not date[1] else {"year": date[0], "month": date[1]},
            "category": category,
            "location": place,
            "polities_involved": polities,
            "description": desc,
        }
        if impact:
            obj["impact"] = impact
        obj["sources"] = srcs
        if end and end[0]:
            obj["end_date"] = {"year": end[0]} if not end[1] else {"year": end[0], "month": end[1]}
        write(DATA / "entities" / "events" / f"{eid[2:]}.yaml", obj)


# Relations
RELATIONS = [
    # 曹魏
    ("p_cao_cao", "p_cao_pi", "father_of", 187, None, None, None, None),
    ("p_cao_cao", "p_cao_rui", "grandfather_of", None, None, None, None, None),
    ("p_cao_cao", "p_caocao_sons", "father_of", 192, None, None, None, None),
    ("p_cao_pi", "p_cao_rui", "father_of", None, None, None, None, None),
    ("p_cao_pi", "k_caowei", "founded", 220, 12, None, None, "代汉建魏"),
    ("p_cao_pi", "d_donghan", "usurped", 220, 12, None, None, "汉献帝禅让"),
    ("p_cao_rui", "k_caowei", "succeeded_by", 226, 6, 239, 1, None),

    ("p_cao_cao", "p_xun_yu", "served_under", 191, None, 212, None, "首席谋臣"),
    ("p_cao_cao", "p_xun_you", "served_under", 196, None, 214, None, None),
    ("p_cao_cao", "p_guo_jia", "served_under", 196, None, 207, None, None),
    ("p_cao_cao", "p_jia_xu", "served_under", 199, None, 220, 3, None),
    ("p_cao_cao", "p_simayi", "served_under", 208, None, 220, 3, None),
    ("p_cao_cao", "p_xiahou_dun", "served_under", 189, None, 220, 3, None),
    ("p_cao_cao", "p_xiahou_yuan", "served_under", 189, None, 219, None, None),
    ("p_cao_cao", "p_zhang_liao", "served_under", 199, None, 220, 3, None),
    ("p_cao_cao", "p_xu_huang", "served_under", 196, None, 220, 3, None),
    ("p_cao_cao", "e_guandu_zhizhan", "led", 200, 2, None, None, "大破袁绍"),
    ("p_cao_cao", "e_chibi_zhizhan", "led", 208, 12, None, None, "战败"),

    # 司马氏代魏
    ("p_simayi", "p_sima_shi", "father_of", 208, None, None, None, None),
    ("p_simayi", "p_sima_zhao", "father_of", 211, None, None, None, None),
    ("p_sima_zhao", "p_simayan", "father_of", 236, None, None, None, None),
    ("p_simayi", "e_sijima_dai_wei", "participated_in", 249, 2, 251, 9, "高平陵之变"),
    ("p_sima_shi", "e_sijima_dai_wei", "participated_in", 251, 3, 255, 3, None),
    ("p_sima_zhao", "e_sijima_dai_wei", "participated_in", 255, 3, 265, 9, None),
    ("p_sima_zhao", "p_liu_shan", "killed", None, None, None, None, "灭蜀(263,邓艾)"),
    ("p_simayan", "k_xijin", "founded", 266, 2, None, None, "代魏建晋"),
    ("p_simayan", "k_caowei", "usurped", 266, 2, None, None, None),
    ("p_simayan", "p_simazhong", "father_of", 259, None, None, None, None),

    # 蜀汉
    ("p_liu_bei", "p_liu_shan", "father_of", 207, None, None, None, None),
    ("p_liu_bei", "k_shuhan", "founded", 221, 4, None, None, None),
    ("p_liu_bei", "p_zhuge_liang", "served_under", 207, None, 223, 4, "托孤"),
    ("p_liu_bei", "p_guan_yu", "served_under", 184, None, 220, 1, "桃园"),
    ("p_liu_bei", "p_zhang_fei", "served_under", 184, None, 221, None, None),
    ("p_liu_bei", "p_zhao_yun", "served_under", 200, None, 223, 4, None),
    ("p_liu_bei", "e_yiling_zhizhan", "led", 222, 8, None, None, "战败"),
    ("p_zhuge_liang", "e_qishan_beifa", "led", 227, 3, 234, 8, "五次北伐"),
    ("p_liu_shan", "p_zhuge_liang", "served_under", 223, 4, 234, 8, "丞相"),
    ("p_jiang_wei", "p_liu_shan", "served_under", 234, 8, 263, 11, None),

    # 东吴
    ("p_sun_jian", "p_sun_ce", "father_of", 175, None, None, None, None),
    ("p_sun_jian", "p_sun_quan", "father_of", 182, None, None, None, None),
    ("p_sun_ce", "p_sun_quan", "sibling_of", None, None, None, None, "兄弟"),
    ("p_sun_quan", "k_dongwu", "founded", 222, None, None, None, "222 称王,229 称帝"),
    ("p_sun_quan", "p_zhou_yu", "served_under", 200, 4, 210, 12, None),
    ("p_sun_quan", "p_lu_su", "served_under", 200, 4, 217, None, None),
    ("p_sun_quan", "p_lv_meng", "served_under", None, None, 220, None, None),
    ("p_sun_quan", "p_lu_xun", "served_under", None, None, 245, None, None),
    ("p_zhou_yu", "e_chibi_zhizhan", "led", 208, 12, None, None, "主帅"),
    ("p_lu_xun", "e_yiling_zhizhan", "led", 222, 8, None, None, "火烧连营"),

    # 三国因果
    ("e_huangjin_qiyi", "e_dong_zhuo_luan_zheng", "preceded_by", None, None, None, None, "黄巾引出军阀混战"),
    ("e_dong_zhuo_luan_zheng", "e_guandu_zhizhan", "preceded_by", None, None, None, None, "群雄并起→官渡"),
    ("e_guandu_zhizhan", "e_chibi_zhizhan", "preceded_by", None, None, None, None, "北方统一→南下"),
    ("e_chibi_zhizhan", "e_yiling_zhizhan", "preceded_by", None, None, None, None, "三国鼎立定型"),

    # 西晋
    ("p_simayan", "p_simazhong", "father_of", 259, None, None, None, None),
    ("p_simazhong", "k_xijin", "succeeded_by", 290, 5, 307, 1, "惠帝"),
    ("p_simazhong", "p_jia_nan_feng", "spouse_of", None, None, None, None, None),
    ("p_jia_nan_feng", "e_bawang_zhiluan", "participated_in", 291, 3, 300, 5, "祸首"),
    ("e_bawang_zhiluan", "e_yongjia_zhiluan", "preceded_by", None, None, None, None, "八王之乱使西晋元气大伤"),
    ("e_yongjia_zhiluan", "e_yiguan_nandu", "preceded_by", None, None, None, None, "永嘉之乱→东晋南渡"),

    # 东晋
    ("p_wang_dao", "e_yiguan_nandu", "participated_in", 317, 3, None, None, "主导"),
    ("p_xie_an", "e_feishui_zhizhan", "led", 383, 11, None, None, "总指挥"),

    # 十六国
    ("p_liu_yuan", "k_hanzhao", "founded", 304, 10, None, None, None),
    ("p_shi_le", "k_houzhao", "founded", 319, 11, None, None, None),
    ("p_fu_jian", "k_qian_qin", "succeeded_by", 357, 6, 385, 10, None),
    ("p_fu_jian", "e_feishui_zhizhan", "led", 383, 11, None, None, "战败"),

    # 南朝
    ("p_liu_yu", "k_liusong", "founded", 420, 7, None, None, "代晋建宋"),
    ("p_liu_yu", "k_dongjin", "usurped", 420, 7, None, None, None),
    ("p_xiao_yan", "k_nan_liang", "founded", 502, 4, None, None, None),
    ("p_xiao_yan", "e_houjing_zhiluan", "participated_in", 548, 8, 549, 5, "被困饿死"),
    ("p_hou_jing", "e_houjing_zhiluan", "participated_in", 548, 8, 552, None, "发动者"),
    ("p_chen_baxian", "e_houjing_zhiluan", "participated_in", 552, None, None, None, "平叛"),
    ("p_chen_baxian", "k_nan_chen", "founded", 557, 10, None, None, None),
    ("p_chen_shubao", "k_nan_chen", "succeeded_by", 582, None, 589, 1, "末代"),

    # 北朝
    ("p_tuoba_gui", "k_beiwei", "founded", 386, 3, None, None, None),
    ("p_tuoba_hong", "e_xiaowendi_hanhua", "participated_in", 494, None, None, None, "主导"),
    ("p_tuoba_hong", "k_beiwei", "succeeded_by", 471, None, 499, 4, "孝文帝"),
    ("p_er_zhu_rong", "e_heyin_zhibian", "participated_in", 528, 4, None, None, "执行者"),
    ("p_gao_huan", "e_beiwei_fenlie", "participated_in", 534, None, None, None, "建东魏"),
    ("p_yuwen_tai", "e_beiwei_fenlie", "participated_in", 534, None, None, None, "建西魏"),
    ("p_gao_huan", "k_dong_wei", "founded", 534, 10, None, None, None),
    ("p_yuwen_tai", "k_xi_wei", "founded", 535, None, None, None, None),
    ("p_yuwen_yong", "k_bei_zhou", "succeeded_by", 560, None, 578, 6, "武帝"),
    ("p_yuwen_yong", "e_beizhou_mie_beiqi", "led", 577, None, None, None, "亲征灭齐"),
    ("p_yuwen_jue", "k_bei_zhou", "founded", 557, 1, None, None, "代西魏建周"),
    ("p_yuwen_jue", "p_yuwen_tai", "father_of", None, None, None, None, None),

    # 六镇 → 关陇集团
    ("e_liuzhen_zhiluan", "f_guanlong", "includes", None, None, None, None, "六镇武人是关陇集团前身"),
    ("e_liuzhen_zhiluan", "e_heyin_zhibian", "preceded_by", None, None, None, None, "六镇乱→尔朱荣起"),

    # 因果链到隋
    ("e_beizhou_mie_beiqi", "e_yangjian_dai_zhou", "preceded_by", None, None, None, None, "北周统一北方→杨坚代周"),

    # 关陇集团成员(补充更多)
    ("p_yuwen_tai", "f_guanlong", "leader_of", 530, None, 556, None, "创立者"),
    ("p_yuwen_jue", "f_guanlong", "member_of", 542, None, 557, None, None),
    ("p_yuwen_yong", "f_guanlong", "member_of", 543, None, 578, 6, None),
    ("p_gao_huan", "f_heshuo_3_zhen", "leader_of", 528, None, 547, 2, "怀朔镇出身,关联河朔系"),
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
    out = DATA / "relations" / "weijin_nanbeichao.yaml"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(deduped, f, allow_unicode=True, sort_keys=False)
    print(f"  ✓ {len(deduped)} relations → data/relations/weijin_nanbeichao.yaml")


if __name__ == "__main__":
    print(f"→ Phase 11: Wei-Jin-Nanbeichao (220-589)")
    gen_places()
    print(f"  ✓ {len(PLACES)} places")
    gen_birthplaces()
    print(f"  ✓ {len(EXTRA_PLACES_BIRTH)} birthplaces")
    gen_polities()
    print(f"  ✓ {len(POLITIES)} polities")
    gen_persons()
    print(f"  ✓ {len(PERSONS)} persons")
    gen_events()
    print(f"  ✓ {len(EVENTS)} events")
    gen_relations()
    print("Done.")
