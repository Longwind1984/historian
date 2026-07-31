#!/usr/bin/env python3
"""Phase 13 — Song Dynasty (960-1279, Northern + Southern).

Covers:
- 北宋 (960-1127): 9 emperors + 开国集团(义社十兄弟) + 庆历/新政/变法 + 理学奠基 + 澶渊之盟
- 南宋 (1127-1279): 9 emperors + 抗金(岳飞韩世忠) + 投降派(秦桧) + 理学集大成 + 崖山
- 辽/金/西夏 cross-state relations
"""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)


# 北宋 + 南宋 + 周边(辽金夏) 皇帝与重要人物
PERSONS = [
    # ===== 北宋皇帝(太祖、太宗已存在) =====
    ("p_zhenzong", "赵恒", ["宋真宗"], None, (968, 12), (1022, 2), "pl_kaifeng",
     "宋真宗。997 继位。1004 辽军南下,寇准力主亲征澶州,1005 澶渊之盟。后期信谶纬,大搞封禅。", ["宋史·真宗本纪"]),
    ("p_renzong", "赵祯", ["宋仁宗"], None, (1010, None), (1063, 3), "pl_kaifeng",
     "宋仁宗。1022-1063 在位 42 年(宋在位最久)。仁宗盛治,范仲淹、欧阳修、包拯等名臣辈出。1043 庆历新政(范)失败。1044 庆历和议与西夏。'仁君'典范。", ["宋史·仁宗本纪"]),
    ("p_yingzong", "赵曙", ["宋英宗"], None, (1032, None), (1067, 1), "pl_kaifeng",
     "宋英宗。仁宗养子。1063 继位,在位 4 年。命司马光设局编修历代君臣事迹(《资治通鉴》之始)。", ["宋史·英宗本纪"]),
    ("p_shenzong", "赵顼", ["宋神宗"], "仲鍼", (1048, 5), (1085, 3), "pl_kaifeng",
     "宋神宗。1067 20 岁继位,锐意富强。1069 起王安石推行熙宁变法。1080-1082 元丰改制。两度伐夏皆败。", "北宋变法的政治推手。", ["宋史·神宗本纪"]),
    ("p_zhezong", "赵煦", ["宋哲宗"], None, (1077, None), (1100, 1), "pl_kaifeng",
     "宋哲宗。1085 9 岁继位,太皇太后高氏垂帘,起司马光废新法(元祐更化)。1093 高氏崩,哲宗亲政复新法(绍圣绍述)。", ["宋史·哲宗本纪"]),
    ("p_huizong", "赵佶", ["宋徽宗"], None, (1082, 11), (1135, 6), "pl_kaifeng",
     "宋徽宗。书画天才(瘦金体、院体画),政治昏聩。用蔡京、童贯、朱勔(六贼)。设苏杭应奉局(花石纲)。1120 方腊、宋江起义。1120 海上之盟联金灭辽。1127 靖康之变掳北上,1135 囚死五国城。", ["宋史·徽宗本纪"]),
    ("p_qinzong", "赵桓", ["宋钦宗"], None, (1100, 5), (1161, None), "pl_kaifeng",
     "宋钦宗。1125/1126 金军南下,徽宗禅位。钦宗优柔,罢李纲,主和。1127 开封城破,与徽宗同被掳(靖康之变),囚燕京至死。", ["宋史·钦宗本纪"]),

    # ===== 南宋皇帝 =====
    ("p_gaozong", "赵构", ["宋高宗"], "德基", (1107, 6), (1187, 11), "pl_kaifeng",
     "宋高宗。徽宗第九子,靖康之变中唯一逃脱的近支皇族。1127 南京应天府即位,改元建炎,南渡。1138 定都临安。1140 岳飞郾城大捷后下十二金牌召还。1141 绍兴和议称臣于金,杀岳飞。1162 禅位孝宗。81 岁善终。", ["宋史·高宗本纪"]),
    ("p_xiaozong", "赵昚", ["宋孝宗"], None, (1127, 11), (1194, 6), "pl_linan_song",
     "宋孝宗。太祖七世孙。1162 高宗禅位。即为岳飞平反,起用张浚。1163 隆兴北伐,符离溃败。1164 隆兴和议(叔侄之国)。乾道淳熙之治,南宋政局最稳。", ["宋史·孝宗本纪"]),
    ("p_guangzong", "赵惇", ["宋光宗"], None, (1147, None), (1200, 9), "pl_linan_song",
     "宋光宗。1189 继位。惧内,与父孝宗失和,精神失常。1194 赵汝愚、韩侂胄拥立其子宁宗,光宗被尊太上皇。", ["宋史·光宗本纪"]),
    ("p_ningzong", "赵扩", ["宋宁宗"], None, (1168, None), (1224, 9), "pl_linan_song",
     "宋宁宗。1194 继位。前期韩侂胄专权,禁道学(庆元党禁)。1206 开禧北伐败。1208 嘉定和议,韩侂胄被杀函首送金。后期史弥远专权。", ["宋史·宁宗本纪"]),
    ("p_lizong", "赵昀", ["宋理宗"], None, (1205, 1), (1264, 11), "pl_linan_song",
     "宋理宗。1224 史弥远拥立。1233 亲政(端平更化),尊崇理学。1234 联蒙灭金。端平入洛失败,宋蒙战争爆发。后期怠政,宠贾似道。", ["宋史·理宗本纪"]),
    ("p_duzong", "赵禥", ["宋度宗"], None, (1240, 5), (1274, 8), "pl_linan_song",
     "宋度宗。1264 继位。智力平庸。贾似道擅权。襄樊被围六年无策。1273 襄阳失陷。", ["宋史·度宗本纪"]),
    ("p_gongdi", "赵㬎", ["宋恭帝"], None, (1271, 9), (1323, None), "pl_linan_song",
     "宋恭帝。1274 4 岁继位,谢太后垂帘,贾似道当国。1276 元军入临安,降。被掳上都,后出家为僧(吐蕃)。", ["宋史·瀛国公本纪"]),
    ("p_duanzong", "赵昰", ["宋端宗"], None, (1269, None), (1278, 5), "pl_yashan2",
     "宋端宗。临安陷落后陆秀夫、张世杰护送南逃。1276 福州即位。元军追击流亡海上,1278 病死,年 10 岁。", ["宋史·本纪47"]),
    ("p_dibing", "赵昺", ["宋末帝", "少帝"], None, (1272, None), (1279, 3), "pl_yashan2",
     "宋末帝。1278 即位,8 岁。1279 崖山海战宋全军覆没,丞相陆秀夫负帝投海。南宋亡。", ["宋史·本纪47"]),

    # ===== 北宋开国集团 =====
    ("p_zhaopu", "赵普", None, "则平", (922, None), (992, 8), "pl_ji_xian_zhaopu",
     "北宋开国谋主。陈桥兵变主要策划者。献'杯酒释兵权'策。太祖、太宗两朝宰相。'半部《论语》治天下'。", ["宋史·赵普传"]),
    ("p_caobin", "曹彬", None, "国华", (931, None), (999, None), "pl_lingyi_caobin",
     "北宋开国名将。灭后蜀(964-965)、灭南唐(974-975)主帅。雍熙北伐东路主帅(986),败。", ["宋史·曹彬传"]),
    ("p_panmei", "潘美", None, "仲询", (925, None), (991, 8), "pl_daming_panmei",
     "北宋开国名将。灭南汉(970)主帅。雍熙北伐西路主帅,因护送百姓撤退致杨业孤军战死陈家谷(986),坐贬。", ["宋史·潘美传"]),
    ("p_shishouxin_song", "石守信", None, None, (928, None), (984, None), "pl_kaifeng",
     "北宋开国元勋,义社十兄弟之一。陈桥兵变内应。961 杯酒释兵权后罢军职。", ["宋史·石守信传"]),
    ("p_yangye", "杨业", ["杨继业", "杨无敌"], None, (None, None), (986, 8), "pl_taiyuan",
     "北宋抗辽名将。原北汉降将。雍熙北伐西路军副帅,陈家谷孤军被俘绝食死。'杨家将'传奇原型。", ["宋史·杨业传"]),

    # ===== 北宋名臣 / 政治家 =====
    ("p_kouzhun", "寇准", None, "平仲", (961, None), (1023, 10), "pl_xiagui_kouzhun",
     "北宋名相。1004 辽军南下,力主真宗亲征澶州,促成澶渊之盟。后遭王钦若排挤,贬死雷州。", ["宋史·寇准传"]),
    ("p_fanzhongyan", "范仲淹", None, "希文", (989, 10), (1052, 6), "pl_suzhou_fan",
     "北宋政治家、文学家、军事家。1040-1043 镇守陕西御西夏(与韩琦并称'韩范')。1043 任参知政事主持庆历新政,一年即罢。'先天下之忧而忧'。", ["宋史·范仲淹传"]),
    ("p_hanqi", "韩琦", None, "稚圭", (1008, None), (1075, 8), "pl_anyang_hanqi",
     "北宋名臣。与范仲淹同御西夏。仁宗、英宗、神宗三朝宰相。反对王安石新法。", ["宋史·韩琦传"]),
    ("p_fubi", "富弼", None, "彦国", (1004, None), (1083, None), "pl_looyang_fubi",
     "北宋名臣。庆历新政参与者。出使辽国谈判(增币代割地)。反对新法。", ["宋史·富弼传"]),
    ("p_ouyangxiu", "欧阳修", None, "永叔", (1007, 8), (1072, 9), "pl_luling_oyxy",
     "北宋文学史学大家。古文运动领袖(唐宋八大家)。与宋祁合修《新唐书》,独撰《新五代史》。主持嘉祐二年科举,选拔苏轼、苏辙、曾巩、程颢、张载。", ["宋史·欧阳修传"]),
    ("p_baozheng", "包拯", ["包希仁", "包青天"], "希仁", (999, None), (1062, 5), "pl_hefei_bao",
     "北宋名臣,以清廉刚直著称。权御史中丞、权知开封府。'包青天'形象原型。", ["宋史·包拯传"]),

    # ===== 苏轼一家 + 唐宋八大家其余 =====
    ("p_suxun_song", "苏洵", None, "明允", (1009, None), (1066, 5), "pl_meishan_song",
     "苏轼、苏辙之父,唐宋八大家之一。27 岁发愤读书。著《权书》《衡论》。", ["宋史·苏洵传"]),
    ("p_sushi_song", "苏轼", ["苏东坡"], "子瞻", (1037, 1), (1101, 8), "pl_meishan_song",
     "北宋文学书画全才(唐宋八大家)。嘉祐二年进士。王安石变法时自请外放。乌台诗案(1079)贬黄州,作前后《赤壁赋》。豪放派词宗。", ["宋史·苏轼传"]),
    ("p_suzhe", "苏辙", None, "子由", (1039, None), (1112, 10), "pl_meishan_song",
     "苏轼弟,唐宋八大家之一。嘉祐二年与兄同登第。官至尚书右丞。", ["宋史·苏辙传"]),
    ("p_zenggong", "曾巩", None, "子固", (1019, None), (1083, 4), "pl_nanfeng_zeng",
     "北宋文学家,唐宋八大家之一。欧阳修门生。", ["宋史·曾巩传"]),
    ("p_wanganshi_song", "王安石(已存在补)", None, None, (None, None), (None, None), None, "", []) if False else None,
    ("p_lvhuiqing", "吕惠卿", None, "吉甫", (1032, None), (1111, None), "pl_jinjiang_lv",
     "王安石变法核心助手(新党)。推行青苗、均输等法。王安石罢相后执政,后与王交恶。", ["宋史·奸臣传·吕惠卿"]),
    ("p_zhangdun", "章惇", None, "子厚", (1035, None), (1105, 11), "pl_pucheng_zhang",
     "新党领袖。哲宗亲政后任相(绍圣绍述),复新法,贬元祐党人。", ["宋史·奸臣传·章惇"]),
    ("p_caijing", "蔡京", None, None, (1047, None), (1126, 8), "pl_xianyou_cai",
     "北宋末权臣。徽宗朝四度拜相。借新法之名聚敛,推行'六贼'乱政(花石纲)。靖康时贬死潭州。", ["宋史·奸臣传·蔡京"]),

    # ===== 理学家(北宋五子) =====
    ("p_zhoudunyi", "周敦颐", None, "茂叔", (1017, None), (1073, 7), "pl_daozhou_zhou",
     "北宋理学开山。著《太极图说》《通书》,融合儒道,提出'无极而太极'宇宙论,为程朱理学奠基。", ["宋史·道学传·周敦颐"]),
    ("p_chenghao", "程颢", None, "伯淳", (1032, None), (1085, 7), "pl_luoyang_cheng",
     "北宋理学奠基人(与弟程颐并称'二程')。提出'天理'为核心。心学渊源。", ["宋史·道学传·程颢"]),
    ("p_chengyi", "程颐", None, "正叔", (1033, None), (1107, 9), "pl_luoyang_cheng",
     "北宋理学奠基人。强调'涵养须用敬'。程朱理学的'程'即指程颐。著《伊川易传》。", ["宋史·道学传·程颐"]),
    ("p_zhangzai", "张载", None, "子厚", (1020, None), (1077, 12), "pl_meixian_zhang",
     "北宋理学关学创始人。著《正蒙》《西铭》。'为天地立心,为生民立命,为往圣继绝学,为万世开太平'(横渠四句)。", ["宋史·张载传"]),

    # ===== 南宋理学(朱陆等) =====
    ("p_zhuxi", "朱熹", None, "元晦", (1130, 10), (1200, 4), "pl_wuyuan_zhu",
     "南宋理学集大成者(程朱理学)。编《四书章句集注》(元后科举定本)。讲学白鹿洞、岳麓书院。宁宗初因韩侂胄'庆元党禁'遭禁。死后平反,从祀孔庙。", ["宋史·道学传·朱熹"]),
    ("p_lujiuyuan", "陆九渊", None, "子静", (1139, None), (1193, 1), "pl_jinjiang_lu",
     "南宋心学开创者。提出'心即理'。1175 鹅湖之会与朱熹辩论(朱陆之辩)。", ["宋史·陆九渊传"]),
    ("p_zhangshi_song", "张栻", None, "敬夫", (1133, None), (1180, 8), "pl_mianzhu_zhang",
     "南宋理学家(湖湘学派)。张浚子。主持岳麓书院。与朱熹、吕祖谦并称'东南三贤'。", ["宋史·张栻传"]),
    ("p_lvzuqian", "吕祖谦", None, "伯恭", (1137, None), (1181, 9), "pl_jinhua_lv",
     "南宋理学家(婺学/金华学派)。组织鹅湖之会。编《宋文鉴》《东莱博议》。", ["宋史·吕祖谦传"]),

    # ===== 北宋科学家 / 文化 =====
    ("p_shenkuo", "沈括", None, "存中", (1031, None), (1095, None), "pl_hangzhou_shen",
     "北宋科学家。著《梦溪笔谈》,涉及天文、数学、地质、医学、活字印刷记载等,'中国科学史上的坐标'。", ["宋史·沈括传"]),
    ("p_bisheng", "毕昇", None, None, (None, None), (None, None), "pl_yingshan_bi",
     "北宋发明家。约 1041-1048 发明胶泥活字印刷术,世界最早活字印刷(比古登堡早约 400 年)。仅见于沈括《梦溪笔谈》。", ["梦溪笔谈"]),

    # ===== 宋辽夏金人物 =====
    ("p_xiaotaihou", "萧绰", ["萧太后", "萧燕燕", "承天太后"], None, (953, None), (1009, 12), "pl_beijing_xiao",
     "辽景宗皇后、圣宗生母。982 临朝称制 27 年。重用耶律休哥、韩德让。1004 亲率军南下,澶渊之盟。辽鼎盛期。", ["辽史·后妃传"]),
    ("p_yelulongxu", "耶律隆绪", ["辽圣宗"], None, (972, None), (1031, 6), "pl_beijing_xiao",
     "辽圣宗。在位 49 年(辽最长)。萧太后临朝及亲政后推行汉化改革。1004 澶州之战,1005 澶渊之盟。辽全盛期。", ["辽史·圣宗本纪"]),
    ("p_lijiqian", "李继迁", None, None, (963, None), (1004, 2), "pl_xiazhou_li",
     "党项族首领,西夏奠基者。李元昊之祖。叛宋附辽。攻取灵州,奠西夏基业。", ["宋史·夏国传"]),
    ("p_lideming", "李德明", None, None, (981, None), (1032, 11), "pl_xiazhou_li",
     "党项首领。李继迁子、李元昊父。受辽封大夏国王、宋封西平王。休养生息,扩张河西。", ["宋史·夏国传"]),
    ("p_liyuanhao", "李元昊", ["赵元昊", "曩霄"], None, (1003, None), (1048, 1), "pl_xiazhou_li",
     "西夏开国皇帝。1038 称帝建国号大夏(西夏)。创西夏文字。1038-1044 三川口、好水川、定川寨三败宋军。1044 庆历和议名义称臣实独立。", ["宋史·夏国传"]),
    ("p_wanyanaguda", "完颜阿骨打", ["完颜旻", "金太祖"], None, (1068, None), (1123, 8), "pl_huining_wya",
     "金朝开国皇帝。女真完颜部首领。1114 起兵反辽,1115 称帝建国号金。1120 攻辽上京。1123 伐辽途中病死。", ["金史·太祖本纪"]),
    ("p_wanyanwuqimai", "完颜吴乞买", ["完颜晟", "金太宗"], None, (1075, None), (1135, 2), "pl_huining_wya",
     "金朝第二代。阿骨打弟。1125 灭辽。两度伐宋(1125、1126),1127 灭北宋(靖康之变)。", ["金史·太宗本纪"]),
    ("p_wanyanliang", "完颜亮", ["海陵王", "金废帝"], None, (1122, None), (1161, 12), "pl_beijing_wyliang",
     "金朝第四代。1149 弑熙宗自立。1153 迁都中都(今北京)。1161 大举攻宋(采石矶败于虞允文),兵变中被部下杀于瓜洲。", ["金史·海陵本纪"]),
    ("p_wanyanyong", "完颜雍", ["金世宗"], None, (1123, None), (1189, 1), "pl_beijing_wyliang",
     "金朝第五代。'小尧舜'。1164 与宋隆兴和议(四十余年和平)。推行'大定之治',金全盛期。", ["金史·世宗本纪"]),
    ("p_wanyanshouxu", "完颜守绪", ["金哀宗"], None, (1198, None), (1234, 2), "pl_caizhou_wysx",
     "金朝末代皇帝。在位十年间蒙古步步紧逼,首都由中都迁汴再迁蔡州。1234 蒙宋联军破蔡州,自缢,金亡。", ["金史·哀宗本纪"]),
    ("p_wanyanwuzhu", "完颜宗弼", ["金兀术", "四太子"], None, (None, None), (1148, None), "pl_beijing_wyliang",
     "金朝宗室、名将。阿骨打第四子。建炎南渡后长期主持攻宋。1130 黄天荡、1140 郾城诸役。后主政,促成 1141 绍兴和议。", ["金史·完颜宗弼传"]),

    # ===== 蒙古/元关键人物(部分已存在 p_hubilai 等)=====
    ("p_chengjisihan", "铁木真", ["成吉思汗", "元太祖"], None, (1162, None), (1227, 8), "pl_kelun_tie",
     "蒙古帝国创建者。1206 统一蒙古各部,称成吉思汗。1211-1215 攻金占中都。1219-1224 第一次西征灭花剌子模。1227 灭西夏途中病死清水。", ["元史·太祖本纪"]),
    ("p_kuotai", "窝阔台", ["元太宗"], None, (1186, None), (1241, 12), "pl_karaktuokuo",
     "成吉思汗第三子、第二代大汗(1229-1241)。1234 联宋灭金。1235 建和林。第二次西征(拔都,征欧洲)。", ["元史·太宗本纪"]),
    ("p_tuolei", "拖雷", ["睿宗"], None, (1193, None), (1232, 9), "pl_kelun_tie",
     "成吉思汗第四子。子蒙哥、忽必烈、旭烈兀、阿里不哥相继为汗。元朝追尊睿宗。", ["元史·睿宗传"]),
    ("p_mengge", "蒙哥", ["元宪宗"], None, (1209, None), (1259, 8), "pl_karaktuokuo",
     "拖雷长子。第四代大汗(1251-1259)。1253 派旭烈兀第三次西征。1258 亲征南宋,合州钓鱼城战死。", ["元史·宪宗本纪"]),
    ("p_yeluchucai", "耶律楚材", None, "晋卿", (1190, 7), (1244, 6), "pl_beijing_ylcj",
     "契丹族,辽东丹王耶律倍八世孙。仕金、后仕蒙古。成吉思汗、窝阔台两朝重臣。主张'以儒治国'。著《湛然居士文集》。", ["元史·耶律楚材传"]),

    # ===== 靖康前后 / 投降派 =====
    ("p_tongguan", "童贯", None, None, (1054, None), (1126, None), "pl_kaifeng",
     "北宋末宦官权臣(六贼之一)。掌兵权二十年。伐夏、平方腊。主持海上之盟联金灭辽,反招金军南下。", ["宋史·宦者传·童贯"]),
    ("p_ligang_song", "李纲", None, "伯纪", (1083, 7), (1140, 2), "pl_shaowu_li",
     "两宋之际主战派名臣。1126 金军围开封,组织开封保卫战。旋被罢。建炎初拜相(75 天),力主抗金,排挤去职。", ["宋史·李纲传"]),
    ("p_zongze", "宗泽", None, "汝霖", (1060, 1), (1128, 7), "pl_yiwu_zong",
     "南宋初抗金名将。靖康中镇守磁州。建炎初任东京(开封)留守,招抚义军,联络两河。三呼'过河'而死。岳飞为其部属。", ["宋史·宗泽传"]),
    ("p_zhangbangchang", "张邦昌", None, None, (1081, None), (1127, 11), "pl_kaifeng",
     "北宋末大臣。靖康之变后金人立为'大楚'傀儡皇帝(在位 32 天)。金退后还政赵构。被高宗赐死。", ["宋史·叛臣传·张邦昌"]),
    ("p_fangla", "方腊", ["方十三"], None, (None, None), (1121, 8), "pl_qingxi_fang",
     "北宋末农民起义首领。1120 睦州青溪起义,以'花石纲'扰民为由,响应者百万,攻占六州五十二县,建元永乐。1121 童贯镇压。", ["宋史·童贯传附方腊"]),
    ("p_songjiang", "宋江", None, None, (None, None), (1122, None), "pl_liangshan_song",
     "北宋末农民起义首领。约 1119 起义于河北、山东。约 1121 被张叔夜招降。《水浒传》原型。", ["宋史·张叔夜传"]),

    # ===== 南宋中兴四将 + 抗金 ===
    ("p_yuefei_song", "岳飞(已存在补)", None, None, (None, None), (None, None), None, "", []) if False else None,
    ("p_hanshizhong", "韩世忠", None, "良臣", (1090, None), (1151, 9), "pl_yan'an_han",
     "南宋抗金名将(中兴四将之一)。1130 黄天荡以八千宋军围困金兀术十万军四十八日。大仪镇大捷(1134)。岳飞冤狱时独面诘秦桧'莫须有'。", ["宋史·韩世忠传"]),
    ("p_lianghongyu", "梁红玉", None, None, (None, None), (1135, None), "pl_kaifeng",
     "韩世忠妾(后夫人)。1130 黄天荡之战亲执桴鼓激励士气。后多次随夫出征。", ["宋史·韩世忠传附"]),
    ("p_zhangjun", "张俊", None, "伯英", (1086, None), (1154, 8), "pl_tianshui_zhang",
     "南宋将领(中兴四将之一)。明受之变勤王。但晚节不保,附秦桧,参与陷害岳飞。岳飞墓前铁跪像之一。", ["宋史·张俊传"]),
    ("p_liuguangshi", "刘光世", None, "平叔", (1086, None), (1142, None), "pl_kaifeng",
     "南宋将领(中兴四将之一)。御金屡有怯战之名。所部'淮西兵变'(郦琼叛)。", ["宋史·刘光世传"]),
    ("p_wujie", "吴玠", None, "晋卿", (1093, None), (1139, 6), "pl_xiaogan_wu",
     "南宋抗金名将。与弟吴璘镇守川陕。1130 和尚原之战大败金兀术(宋军首胜)。保住四川。", ["宋史·吴玠传"]),
    ("p_wulin", "吴璘", None, "唐卿", (1102, None), (1167, 6), "pl_xiaogan_wu",
     "南宋将领,吴玠之弟。兄死后独镇川陕三十余年。隆兴北伐时收复十六州。", ["宋史·吴璘传"]),
    ("p_qinkuai", "秦桧", None, "会之", (1090, None), (1155, 11), "pl_jiangning_qin",
     "南宋权相、投降派首领。靖康被掳北上,后金遣归。1131 拜相。绍兴和议(1141)主持者。以'莫须有'罪杀岳飞。专国 19 年。'四大奸臣'之一。", ["宋史·奸臣传·秦桧"]),

    # ===== 南宋后期 + 末年 =====
    ("p_jiasidao", "贾似道", None, "师宪", (1213, 8), (1275, 8), "pl_taizhou_jia",
     "南宋末权相。1259 鄂州之战虚报战功,拜相。推行公田法、打算法,扰民。瞒报襄樊被围。1275 丁家洲之战溃败,被贬,途中被郑虎臣所杀。", ["宋史·奸臣传·贾似道"]),
    ("p_luyou", "陆游", None, "务观", (1125, 11), (1210, 12), "pl_shanyin_lu",
     "南宋爱国诗人。现存诗九千余首(宋诗人第一)。力主抗金,屡遭排挤。临终《示儿》。", ["宋史·陆游传"]),
    ("p_xinqiji", "辛弃疾", None, "幼安", (1140, 5), (1207, 10), "pl_jinan_xin",
     "南宋爱国词人、军事将领。济南人,22 岁聚义抗金,擒叛将南归。力主北伐,在朝遭排挤。豪放派词宗。", ["宋史·辛弃疾传"]),
    ("p_liqingzhao", "李清照", None, None, (1084, None), (1155, None), "pl_jinan_li",
     "两宋之际女词人。婉约派代表。父李格非,夫赵明诚。靖康之变后南渡。著《漱玉词》。'千古第一才女'。", ["宋史(无传)"]),
    ("p_wentianxiang", "文天祥", None, "履善", (1236, 6), (1283, 1), "pl_luling_wen",
     "南宋末政治家、文学家、民族英雄。宝祐四年(1256)状元。1275 起兵勤王。1278 兵败被俘。狱中作《正气歌》。拒降元,1283 就义于大都柴市口。'人生自古谁无死'。", ["宋史·文天祥传"]),
    ("p_luxiufu", "陆秀夫", None, "君实", (1236, None), (1279, 3), "pl_jianhu_lu",
     "南宋末丞相。1276 临安陷落后,与陈宜中在福州拥立端宗,流亡海上。崖山海战宋军败,负 8 岁帝昺投海殉国。", ["宋史·陆秀夫传"]),
    ("p_zhangshijie", "张世杰", None, None, (None, None), (1279, 3), "pl_fanyu_zhang",
     "南宋末将领。1276 后率水军坚持抗元。崖山海战兵败,突围遇风暴溺亡。'宋末三杰'之一。", ["宋史·张世杰传"]),
]
PERSONS = [p for p in PERSONS if p is not None and not p[0].endswith(("_existing", "_add", "_pre"))]


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
        if pid in ("p_xiaotaihou", "p_lianghongyu", "p_liqingzhao"):
            obj["gender"] = "female"
        if birthplace:
            obj["birthplace"] = birthplace
        obj["bio"] = bio
        if significance:
            obj["ext"] = {"significance": significance}
        obj["sources"] = srcs
        write(DATA / "entities" / "persons" / f"{pid[2:]}.yaml", obj)


# 政权
POLITIES = [
    ("k_beisong", "北宋", "Northern Song", "#f1c40f", (960, 2), (1127, 3), "p_zhaokuangyin", "pl_kaifeng", None, "k_jin_jurchen",
     "赵匡胤陈桥兵变代后周。都汴梁。979 灭北汉完成本部统一。1127 金军破开封,掳徽钦二帝(靖康之变),北宋亡。", "宋史"),
    ("k_nansong", "南宋", "Southern Song", "#f39c12", (1127, 5), (1279, 2), "p_gaozong", "pl_linan_song", None, "d_yuan",
     "赵构建炎元年应天府即位,后南渡定都临安(杭州)。1141 绍兴和议与金对峙。1279 崖山海战亡于元。", "宋史"),
    ("k_jin_jurchen2", "金(标识重复使用 k_jin_jurchen)", None, None, (None, None), (None, None), None, None, None, None, "", []) if False else None,
    ("k_xixia", "西夏", "Western Xia", "#8e44ad", (1038, 10), (1227, None), "p_liyuanhao", "pl_xingqing_xixia", None, "d_yuan",
     "党项族政权。1038 李元昊称帝建国号大夏。1044 庆历和议。1227 蒙古灭夏。", "宋史·夏国传"),
]
POLITIES = [p for p in POLITIES if p is not None and p[0] != "k_jin_jurchen2"]


def gen_polities():
    for tup in POLITIES:
        pid, name, en, color, founded, ended, founder, capital, supplanted, ended_by, desc, src = tup
        obj = {
            "id": pid, "type": "Polity", "name": name,
            "name_en": en, "color": color,
            "founded": {"year": founded[0], "month": founded[1]} if founded[1] else {"year": founded[0]},
            "ended": {"year": ended[0], "month": ended[1]} if ended[1] else {"year": ended[0]},
            "capital": capital,
            "description": desc,
            "sources": src.split(";") if isinstance(src, str) else src,
        }
        if founder:
            obj["founder"] = founder
        if supplanted:
            obj["supplanted"] = supplanted
        if ended_by:
            obj["ended_by"] = ended_by
        write(DATA / "entities" / "polities" / f"{pid[2:]}.yaml", obj)


# 派系
FACTIONS = [
    ("f_yishe_shixiongdi", "义社十兄弟", "military_clan", (950, None), (976, None), "pl_kaifeng",
     "后周殿前司中赵匡胤与九位禁军高级将领结拜集团。陈桥兵变的核心力量。宋建立后多数被'杯酒释兵权'。",
     "北宋开国军功集团,陈桥兵变的主导力量。",
     ["赵匡胤", "石守信", "王审琦", "李继勋", "韩重斌"], "950s-960s"),
    ("f_xin_jiu_dang", "新党 vs 旧党", "political", (1069, None), (1126, None), "pl_kaifeng",
     "王安石变法引发的北宋最大党争。新党(变法派):王安石、吕惠卿、曾布、章惇、蔡京;旧党(反变法):司马光、文彦博、韩琦、富弼、欧阳修、苏轼。",
     "北宋中后期政治主轴,党争内耗削弱国力。",
     ["王安石", "司马光", "吕惠卿", "章惇", "蔡京", "苏轼"], "1069-1126"),
    ("f_yuanyou_dangren", "元祐党人", "political", (1086, None), (1126, None), "pl_kaifeng",
     "元祐年间(1086-1094)执政、被哲宗亲政及徽宗朝列为'奸党'的旧党人物。崇宁元年(1102)蔡京立'元祐党人碑',列司马光、苏轼、苏辙、黄庭坚、秦观、程颐等 309 人。",
     "北宋党争顶峰,文化压制,士大夫群体受重创。",
     ["司马光", "苏轼", "苏辙", "黄庭坚", "程颐"], "1102-1105"),
    ("f_zhuzhan_touxiang", "南宋主战派 vs 投降派", "political", (1127, None), (1279, None), "pl_linan_song",
     "南宋政治长期在抗金/抗蒙与求和偏安间拉锯。主战派:李纲、宗泽、岳飞、韩世忠、张浚、辛弃疾、陆游;主和派:秦桧、贾似道。",
     "影响南宋对金、对蒙政策的根本路线之争。",
     ["岳飞", "韩世忠", "秦桧", "张浚", "贾似道"], "1127-1279"),
    ("f_daoxue_pai", "理学(道学)派", "scholarly", (1030, None), None, "pl_jiangnan",
     "北宋周敦颐、张载、二程奠基;南宋朱熹集大成(闽学/程朱理学)、陆九渊创心学。元后程朱理学成科举定式。",
     "主导中国思想六七百年。",
     ["周敦颐", "程颐", "程颢", "张载", "朱熹", "陆九渊"], "1030-1279"),
    ("f_zhusi_han", "主战 vs 投降派(标记)", "political", (None, None), (None, None), None, "", "", [], "") if False else None,
]
FACTIONS = [f for f in FACTIONS if f is not None and not f[0].startswith("f_zhusi_han")]


def gen_factions():
    for tup in FACTIONS:
        fid, name, nature, founded, dissolved, region, desc, sig, members, peak = tup
        obj = {"id": fid, "type": "Faction", "name": name, "nature": nature}
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
        obj["sources"] = ["宋史", "续资治通鉴长编"]
        write(DATA / "entities" / "factions" / f"{fid[2:]}.yaml", obj)


# 战役
BATTLES = [
    ("b_gaolianghe", "高梁河之战", (979, 7), None, "pl_youzhou",
     ["k_beisong", "k_liao"], ["p_zhaoguangyi"], "k_liao", None,
     "太宗灭北汉后径攻辽之南京幽州。围城半月不下。辽将耶律休哥来援,高梁河畔大败宋军。太宗股中两箭,驴车逃归。",
     "北宋首次重大军事失利,基本宣告武力收复燕云无望。",
     "宋史·太宗本纪;辽史·景宗本纪"),
    ("b_yongxi_beifa", "雍熙北伐", (986, 3), (986, 7), "pl_yanyan_zhou",
     ["k_beisong", "k_liao"], ["p_caobin", "p_panmei", "p_yangye"], "k_liao", None,
     "太宗三路伐辽。曹彬冒进粮尽退兵,再进又败于岐沟关;西路军杨业孤军陈家谷被俘绝食死。",
     "宋对辽转入全面守势,'积弱'格局定。",
     "宋史·杨业传"),
    ("b_sanchuankou", "三川口之战", (1040, None), None, "pl_yanzhou_xixia",
     ["k_beisong", "k_xixia"], ["p_liyuanhao"], "k_xixia", "p_liyuanhao",
     "西夏元昊围延州,宋军万余援军于三川口遭夏军伏击,全军覆没。",
     "宋夏战争宋方首败。促范仲淹、韩琦经略陕西。",
     "宋史·夏国传"),
    ("b_haoshuigu", "好水川之战", (1041, 3), None, "pl_ningxia_haoshui",
     ["k_beisong", "k_xixia"], ["p_hanqi", "p_liyuanhao"], "k_xixia", "p_liyuanhao",
     "韩琦命任福率军追击,好水川遭夏军伏击,任福父子战死,宋军丧万余人。",
     "宋史·夏国传", "宋夏"),
    ("b_dingchuanzhai", "定川寨之战", (1042, None), None, "pl_dingchuanzhai",
     ["k_beisong", "k_xixia"], ["p_liyuanhao"], "k_xixia", "p_liyuanhao",
     "西夏大举攻镇戎军,宋将葛怀敏轻敌中伏全军覆没。三川口、好水川、定川寨合称'陕西三大败'。",
     "促庆历和议", "宋史·夏国传"),
    ("b_huangtiandang", "黄天荡之战", (1130, 4), (1130, 5), "pl_huangtiandang",
     ["k_nansong", "k_jin_jurchen"], ["p_hanshizhong", "p_lianghongyu", "p_wanyanwuzhu"], None, "p_hanshizhong",
     "金兀术焚临安北撤,韩世忠率八千于镇江封锁长江,围困金军十万于黄天荡 48 日。梁红玉击鼓助战。",
     "金此后不敢轻易渡江。",
     "宋史·韩世忠传"),
    ("b_yancheng", "郾城大捷", (1140, 7), None, "pl_yancheng",
     ["k_nansong", "k_jin_jurchen"], ["p_yuefei", "p_wanyanwuzhu"], "k_nansong", "p_yuefei",
     "岳飞北伐,驻郾城。金兀术率铁浮图、拐子马。岳飞命岳云、杨再兴迎战,以麻扎刀、大斧专砍马腿,大破金军。颍昌再捷。",
     "南宋抗金最大胜利之一。然高宗、秦桧连下十二金牌召岳飞班师。",
     "宋史·岳飞传"),
    ("b_caizhou_jinmie", "蔡州之战(金亡)", (1234, 2), None, "pl_caizhou_wysx",
     ["k_jin_jurchen", "d_yuan", "k_nansong"], ["p_wanyanshouxu"], "d_yuan", None,
     "金哀宗弃汴走蔡州。蒙古与南宋联军围蔡州三月。城破。哀宗传位完颜承麟后自缢,金亡。",
     "金朝(1115-1234)灭亡,立国 119 年。",
     "金史·哀宗本纪"),
    ("b_xiangfan", "襄樊之战", (1267, None), (1273, 3), "pl_xiangfan",
     ["k_nansong", "d_yuan"], [], "d_yuan", None,
     "元(蒙古)军围襄阳、樊城六年(1267-1273)。宋将吕文焕坚守。1273 樊城先破,襄阳孤立降。",
     "襄阳失陷后南宋门户洞开,6 年后灭宋。",
     "宋史·度宗本纪"),
    ("b_yashan", "崖山海战", (1279, 3), None, "pl_yashan2",
     ["k_nansong", "d_yuan"], ["p_luxiufu", "p_zhangshijie"], "d_yuan", None,
     "1278 南宋流亡朝廷退至崖山。1279 元将张弘范率水陆大军围攻。宋军千余艘战船连成水寨。决战宋军全军覆没。",
     "丞相陆秀夫负 8 岁帝昺投海,从死者十余万。南宋亡。中国首次完全被北方游牧民族政权征服。",
     "宋史·本纪47"),
]


def gen_battles():
    for tup in BATTLES:
        bid, name, date, end, place, combatants, commanders, victor, victor_cmd, desc, *rest = tup
        if len(rest) == 2:
            sig, srcs = rest
        else:
            sig, srcs = rest[0], rest[1] if len(rest) > 1 else ""
        obj = {
            "id": bid, "type": "Battle", "name": name,
            "date": {"year": date[0]} if not date[1] else {"year": date[0], "month": date[1]},
            "location": place,
            "combatants": combatants,
            "commanders": commanders,
            "victor": victor,
            "victor_commander": victor_cmd,
            "description": desc,
            "significance": sig,
            "sources": srcs.split(";") if isinstance(srcs, str) else srcs,
        }
        if end and end[0]:
            obj["end_date"] = {"year": end[0]} if not end[1] else {"year": end[0], "month": end[1]}
        write(DATA / "entities" / "battles" / f"{bid[2:]}.yaml", obj)


# 事件
EVENTS = [
    ("e_beijiu_shibingquan", "杯酒释兵权", (961, 7), None, "institution", "pl_kaifeng", ["k_beisong"],
     "赵匡胤宴请石守信、王审琦、高怀德等高级将领,以'君臣两无猜疑'为由,劝其交出兵权,出守外藩。",
     "结束唐末五代武将专权、藩镇割据传统,确立宋代'重文抑武'国策。",
     "续资治通鉴长编·卷2"),
    ("e_chanyuan_zhimeng", "澶渊之盟", (1005, 1), None, "treaty", "pl_chanzhou", ["k_beisong", "k_liao"],
     "1004 辽圣宗、萧太后亲率军南下,寇准力主真宗亲征至澶州。宋军射杀辽将萧挞凛。议和:宋辽约为兄弟之国(宋为兄),宋每年输辽银 10 万两、绢 20 万匹。",
     "宋辽维持和平约 120 年(至 1120 海上之盟)。开启'岁币'外交模式。",
     "宋史·真宗本纪"),
    ("e_qingli_hexi", "庆历和议", (1044, 10), None, "treaty", "pl_xi_an", ["k_beisong", "k_xixia"],
     "西夏三败宋军后宋夏议和。元昊名义向宋称臣(受封夏国主),宋每年赐银 7.2 万两、绢 15.3 万匹、茶 3 万斤。",
     "宋夏西北边境相对稳定约 20 年。",
     "宋史·夏国传"),
    ("e_qingli_xinzheng", "庆历新政", (1043, None), (1045, None), "reform", "pl_kaifeng", ["k_beisong"],
     "范仲淹任参知政事,主持'明黜陟、抑侥幸、厚农桑'等十事改革。触犯权贵,一年即罢。",
     "北宋首次重大政治改革尝试,为王安石变法前奏。",
     "宋史·范仲淹传"),
    ("e_xining_bianfa", "王安石变法(熙宁变法)", (1069, 2), (1085, 3), "reform", "pl_kaifeng", ["k_beisong"],
     "神宗任王安石参知政事推行改革。设'制置三司条例司'。新法:青苗、募役、方田均税、农田水利、市易、均输(理财);保甲、保马、将兵(军事);改革科举(育才)。",
     "增加财政收入,加强军事,但因执行扭曲、党争效果有限。新党旧党长期互斗。",
     "宋史·王安石传"),
    ("e_yuanyou_dangzheng_song", "元祐党争", (1086, None), (1100, None), "institution", "pl_kaifeng", ["k_beisong"],
     "1085 神宗崩,高太后临朝,起司马光为相,废新法(元祐更化)。1093 高氏崩,哲宗亲政复新法(绍圣绍述),元祐党人遭大规模贬斥。",
     "北宋政治长期内耗,削弱国力。",
     "宋史·哲宗本纪"),
    ("e_yuanyou_dangbei", "元祐党人碑", (1102, None), None, "institution", "pl_kaifeng", ["k_beisong"],
     "崇宁元年(1102)蔡京立'元祐党人碑',刻司马光、文彦博、苏轼、苏辙、黄庭坚、秦观、程颐等 309 人,禁其子孙仕宦。",
     "北宋党争顶峰,文化压制。",
     "宋史·徽宗本纪"),
    ("e_haishang_zhimeng", "海上之盟", (1120, None), None, "diplomacy", "pl_dengzhou", ["k_beisong", "k_jin_jurchen"],
     "北宋遣使自登州渡海与金相约夹攻辽:金取辽中京、宋取辽燕京;灭辽后宋收回燕云十六州,以原给辽的岁币转给金。但宋军攻燕京失败,请金代取,金遂知宋军虚弱。",
     "辽灭亡(1125),金觉察宋腐败,旋即南下,致靖康之变。",
     "宋史·徽宗本纪;三朝北盟会编"),
    ("e_jingkang_zhibian", "靖康之变", (1127, 3), None, "coup", "pl_kaifeng", ["k_beisong", "k_jin_jurchen"],
     "1125 金军分两路南侵。1126 围开封,李纲守御,金军退后又至。1127 正月开封城破。三月金军掳徽宗、钦宗二帝及皇室三千余人北去,掠尽财宝典籍百工。北宋亡。",
     "中国历史重大转折,南北分立。'靖康耻'。",
     "宋史·钦宗本纪"),
    ("e_jianyan_nandu", "建炎南渡", (1127, 5), None, "succession", "pl_yingtianfu", ["k_nansong"],
     "1127 五月徽宗第九子康王赵构在南京应天府即位,改元建炎,是为高宗,南宋始。1138 定都临安。",
     "开启南宋偏安一百五十余年局面。",
     "宋史·高宗本纪"),
    ("e_shaoxing_heyi", "绍兴和议", (1141, 11), None, "treaty", "pl_linan_song", ["k_nansong", "k_jin_jurchen"],
     "高宗、秦桧主和。约定:宋向金称臣;宋每年贡银 25 万两、绢 25 万匹;东以淮水、西以大散关为界。为促成和议,秦桧以'莫须有'罪杀岳飞(1142.1)。",
     "宋金正式划定边界,南宋偏安格局确立。",
     "宋史·高宗本纪"),
    ("e_longxing_beifa", "隆兴北伐(符离之溃)", (1163, 5), (1163, 7), "coup", "pl_xiaoxian", ["k_nansong", "k_jin_jurchen"],
     "孝宗起用张浚主持北伐。宋军三路出师。李显忠、邵宏渊失和,符离大溃,丧师十余万。次年隆兴和议(叔侄之国,岁币减)。",
     "宋史·孝宗本纪", ""),
    ("e_kaixi_beifa", "开禧北伐", (1206, 5), (1208, None), "coup", "pl_linan_song", ["k_nansong", "k_jin_jurchen"],
     "韩侂胄秉政,准备北伐。1206 分路出击,四川吴曦叛降金,诸路皆败。1208 史弥远杀韩侂胄函首送金。嘉定和议:增岁币,伯侄之国。",
     "宋史·宁宗本纪", ""),
    ("e_lianmeng_miejin", "联蒙灭金", (1233, None), (1234, 2), "diplomacy", "pl_caizhou_wysx", ["k_nansong", "d_yuan", "k_jin_jurchen"],
     "蒙古联宋灭金。1233 宋蒙围蔡州。1234 正月城破,金哀宗自缢,金亡。宋收复汴京、洛阳应天三京(端平入洛),旋被蒙军击败。",
     "金亡,但宋失去金作缓冲,直接面对蒙古,44 年后南宋亡。",
     "宋史·理宗本纪"),
    ("e_yashan_zhibian", "崖山海战(南宋亡)", (1279, 3), None, "coup", "pl_yashan2", ["k_nansong", "d_yuan"],
     "1278 南宋流亡朝廷退至崖山。1279 元将张弘范率水陆大军围攻。宋军千余艘战船连成水寨,被围断水二十余日。决战宋军全军覆没。丞相陆秀夫负 8 岁帝昺投海,从死者十余万。",
     "南宋亡。中国首次完全被北方游牧民族政权征服。",
     "宋史·本纪47"),
]


def gen_events():
    for tup in EVENTS:
        eid, name, date, end, category, place, polities, desc, impact, srcs = tup[:10]
        obj = {
            "id": eid, "type": "Event", "name": name,
            "date": {"year": date[0]} if not date[1] else {"year": date[0], "month": date[1]},
            "category": category,
            "location": place,
            "polities_involved": polities,
            "description": desc,
            "impact": impact,
            "sources": srcs.split(";") if isinstance(srcs, str) else srcs,
        }
        if end and end[0]:
            obj["end_date"] = {"year": end[0]} if not end[1] else {"year": end[0], "month": end[1]}
        write(DATA / "entities" / "events" / f"{eid[2:]}.yaml", obj)


# 地点
PLACES = [
    ("pl_linan_song", "临安", "杭州", "浙江", 30.27, 120.16, "capital", [], "南宋都城"),
    ("pl_yashan2", "崖山", "新会", "广东", 22.51, 113.04, "battlefield", [], "1279 崖山海战"),
    ("pl_yingtianfu", "南京应天府", "商丘", "河南", 34.44, 115.65, "city", [], "南宋初立都"),
    ("pl_chanzhou", "澶州", "濮阳", "河南", 35.76, 115.03, "battlefield", [], "1004-1005 澶渊之战"),
    ("pl_caizhou_wysx", "蔡州", "汝南", "河南", 33.00, 114.36, "battlefield", [], "1234 金亡地"),
    ("pl_xiangfan", "襄樊", "襄阳", "湖北", 32.04, 112.12, "battlefield", [], "1267-1273 襄樊之战"),
    ("pl_huangtiandang", "黄天荡", "南京", "江苏", 32.10, 118.90, "battlefield", [], "1130 黄天荡之战"),
    ("pl_yancheng", "郾城", "漯河", "河南", 33.59, 114.02, "battlefield", [], "1140 郾城大捷"),
    ("pl_xingqing_xixia", "兴庆府", "银川", "宁夏", 38.49, 106.23, "capital", [], "西夏都城"),
    ("pl_huining_wya", "会宁府", "阿城", "黑龙江", 45.55, 126.97, "capital", [], "金早期都"),
    ("pl_yanzhou_xixia", "延州", "延安", "陕西", 36.60, 109.49, "battlefield", [], "三川口之战"),
    ("pl_ningxia_haoshui", "好水川", "隆德", "宁夏", 35.62, 106.12, "battlefield", [], "1041 好水川"),
    ("pl_dingchuanzhai", "定川寨", "固原", "宁夏", 36.16, 106.24, "battlefield", [], "1042 定川寨"),
    ("pl_yanyan_zhou", "燕云", "北京/大同", "河北/山西", 39.90, 116.40, "region", [], "雍熙北伐"),
    ("pl_youzhou_song", "幽州", "北京", "北京", 39.91, 116.40, "city", [], "高梁河"),
    ("pl_dengzhou", "登州", "蓬莱", "山东", 37.81, 120.76, "city", [], "海上之盟出发地"),
    ("pl_xiaoxian", "符离", "宿州", "安徽", 33.62, 116.95, "battlefield", [], "隆兴北伐"),
    ("pl_xi_an", "西安(西夏相关)", "银川", "宁夏", 38.49, 106.23, "city", [], "庆历和议"),

    # 人物籍贯地
    ("pl_ji_xian_zhaopu", "蓟", "天津", "天津", 39.99, 117.51, "birthplace", [], "赵普祖籍"),
    ("pl_lingyi_caobin", "灵寿", "灵寿", "河北", 38.31, 114.27, "birthplace", [], "曹彬籍贯"),
    ("pl_daming_panmei", "大名", "大名", "河北", 36.28, 115.14, "birthplace", [], "潘美籍贯"),
    ("pl_xiagui_kouzhun", "下邽", "渭南", "陕西", 34.50, 109.51, "birthplace", [], "寇准籍贯"),
    ("pl_suzhou_fan", "苏州吴县", "苏州", "江苏", 31.30, 120.62, "birthplace", [], "范仲淹籍贯"),
    ("pl_anyang_hanqi", "相州", "安阳", "河南", 36.10, 114.39, "birthplace", [], "韩琦籍贯"),
    ("pl_looyang_fubi", "洛阳", "洛阳", "河南", 34.62, 112.45, "birthplace", [], "富弼籍贯"),
    ("pl_luling_oyxy", "庐陵", "吉安", "江西", 27.11, 114.99, "birthplace", [], "欧阳修籍贯"),
    ("pl_hefei_bao", "合肥", "合肥", "安徽", 31.82, 117.27, "birthplace", [], "包拯籍贯"),
    ("pl_meishan_song", "眉州", "眉山", "四川", 30.08, 103.83, "birthplace", [], "三苏籍贯"),
    ("pl_nanfeng_zeng", "南丰", "南丰", "江西", 27.22, 116.57, "birthplace", [], "曾巩籍贯"),
    ("pl_jinjiang_lv", "晋江", "泉州", "福建", 24.87, 118.68, "birthplace", [], "吕惠卿/吕祖谦/陆九渊籍贯"),
    ("pl_pucheng_zhang", "浦城", "浦城", "福建", 27.92, 118.55, "birthplace", [], "章惇籍贯"),
    ("pl_xianyou_cai", "仙游", "仙游", "福建", 25.36, 118.70, "birthplace", [], "蔡京籍贯"),
    ("pl_daozhou_zhou", "道州", "道县", "湖南", 25.52, 111.57, "birthplace", [], "周敦颐籍贯"),
    ("pl_luoyang_cheng", "洛阳", "洛阳", "河南", 34.62, 112.45, "birthplace", [], "二程籍贯"),
    ("pl_meixian_zhang", "郿县", "眉县", "陕西", 34.27, 107.75, "birthplace", [], "张载籍贯"),
    ("pl_wuyuan_zhu", "婺源", "婺源", "江西", 29.25, 117.86, "birthplace", [], "朱熹籍贯"),
    ("pl_mianzhu_zhang", "绵竹", "绵竹", "四川", 31.30, 104.21, "birthplace", [], "张栻籍贯"),
    ("pl_jinhua_lv", "金华", "金华", "浙江", 29.08, 119.65, "birthplace", [], "吕祖谦籍贯"),
    ("pl_hangzhou_shen", "杭州", "杭州", "浙江", 30.27, 120.16, "birthplace", [], "沈括籍贯"),
    ("pl_yingshan_bi", "英山", "英山", "湖北", 30.74, 115.68, "birthplace", [], "毕昇籍贯"),
    ("pl_beijing_xiao", "幽州/北京", "北京", "北京", 39.91, 116.40, "birthplace", [], "萧太后籍贯"),
    ("pl_xiazhou_li", "夏州", "靖边", "陕西", 37.60, 108.79, "birthplace", [], "党项李氏"),
    ("pl_beijing_wyliang", "中都", "北京", "北京", 39.91, 116.40, "capital", [], "海陵王迁都"),
    ("pl_caizhou_wysx2", "蔡州", "汝南", "河南", 33.00, 114.36, "city", [], "哀宗亡地"),
    ("pl_kelun_tie", "斡难河", "鄂嫩河", "蒙古", 49.40, 109.30, "birthplace", [], "成吉思汗发源地"),
    ("pl_karaktuokuo", "和林", "哈尔和林", "蒙古", 47.30, 102.83, "capital", [], "窝阔台建"),
    ("pl_beijing_ylcj", "燕京", "北京", "北京", 39.91, 116.40, "birthplace", [], "耶律楚材籍贯"),
    ("pl_shaowu_li", "邵武", "邵武", "福建", 27.34, 117.49, "birthplace", [], "李纲籍贯"),
    ("pl_yiwu_zong", "义乌", "义乌", "浙江", 29.30, 120.07, "birthplace", [], "宗泽籍贯"),
    ("pl_qingxi_fang", "青溪", "淳安", "浙江", 29.61, 119.04, "battlefield", [], "方腊起兵地"),
    ("pl_liangshan_song", "梁山泺", "梁山", "山东", 35.80, 116.10, "battlefield", [], "宋江活动地"),
    ("pl_yan'an_han", "延安", "延安", "陕西", 36.60, 109.49, "birthplace", [], "韩世忠籍贯"),
    ("pl_tianshui_zhang", "天水", "天水", "甘肃", 34.58, 105.72, "birthplace", [], "张俊籍贯"),
    ("pl_xiaogan_wu", "孝感", "孝感", "湖北", 30.92, 113.92, "birthplace", [], "吴玠籍贯"),
    ("pl_jiangning_qin", "江宁", "南京", "江苏", 32.04, 118.78, "birthplace", [], "秦桧籍贯"),
    ("pl_taizhou_jia", "台州", "台州", "浙江", 28.66, 121.66, "birthplace", [], "贾似道籍贯"),
    ("pl_shanyin_lu", "山阴", "绍兴", "浙江", 30.00, 120.58, "birthplace", [], "陆游籍贯"),
    ("pl_jinan_xin", "济南", "济南", "山东", 36.65, 117.00, "birthplace", [], "辛弃疾/李清照籍贯"),
    ("pl_jinan_li", "济南", "济南", "山东", 36.65, 117.00, "birthplace", [], "李清照籍贯"),
    ("pl_luling_wen", "庐陵", "吉安", "江西", 27.11, 114.99, "birthplace", [], "文天祥籍贯"),
    ("pl_jianhu_lu", "建湖", "建湖", "江苏", 33.47, 119.80, "birthplace", [], "陆秀夫籍贯"),
    ("pl_fanyu_zhang", "范阳", "涿州", "河北", 39.49, 115.98, "birthplace", [], "张世杰籍贯"),
]


def gen_places():
    for tup in PLACES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["宋史·地理志", "辽史·地理志", "金史·地理志", "元史·地理志", "中国历史地图集"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# Relations
RELATIONS = [
    # 北宋帝系
    ("p_zhaokuangyin", "p_zhaoguangyi", "sibling_of", None, None, None, None, "兄弟"),
    ("p_zhaoguangyi", "p_zhenzong", "father_of", 968, 12, None, None, None),
    ("p_zhaoguangyi", "p_zhenzong", "succeeded_by", 997, 3, 1022, 2, None),
    ("p_zhenzong", "p_renzong", "succeeded_by", 1022, 2, 1063, 3, None),
    ("p_zhenzong", "p_renzong", "father_of", 1010, None, None, None, None),
    ("p_renzong", "p_yingzong", "succeeded_by", 1063, 4, 1067, 1, "养子入继"),
    ("p_yingzong", "p_shenzong", "succeeded_by", 1067, 1, 1085, 3, None),
    ("p_yingzong", "p_shenzong", "father_of", 1048, 5, None, None, None),
    ("p_shenzong", "p_zhezong", "succeeded_by", 1085, 3, 1100, 1, None),
    ("p_shenzong", "p_huizong", "father_of", 1082, 11, None, None, None),
    ("p_shenzong", "p_zhezong", "father_of", 1077, None, None, None, None),
    ("p_zhezong", "p_huizong", "succeeded_by", 1100, 1, 1125, 12, None),
    ("p_huizong", "p_qinzong", "succeeded_by", 1125, 12, 1127, 3, "禅位"),
    ("p_huizong", "p_qinzong", "father_of", 1100, 5, None, None, None),
    ("p_huizong", "p_gaozong", "father_of", 1107, 6, None, None, "第九子"),

    # 南宋帝系
    ("p_gaozong", "p_xiaozong", "succeeded_by", 1162, None, None, None, "禅位,养子"),
    ("p_xiaozong", "p_guangzong", "succeeded_by", 1189, None, 1194, None, None),
    ("p_xiaozong", "p_guangzong", "father_of", 1147, None, None, None, None),
    ("p_guangzong", "p_ningzong", "succeeded_by", 1194, None, 1224, 9, None),
    ("p_guangzong", "p_ningzong", "father_of", 1168, None, None, None, None),
    ("p_ningzong", "p_lizong", "succeeded_by", 1224, None, 1264, 11, "史弥远拥立"),
    ("p_lizong", "p_duzong", "succeeded_by", 1264, 11, 1274, 8, None),
    ("p_lizong", "p_duzong", "father_of", None, None, None, None, "侄"),
    ("p_duzong", "p_gongdi", "succeeded_by", 1274, 8, 1276, None, None),
    ("p_duzong", "p_gongdi", "father_of", 1271, 9, None, None, None),
    ("p_duzong", "p_duanzong", "father_of", 1269, None, None, None, None),
    ("p_duzong", "p_dibing", "father_of", 1272, None, None, None, None),
    ("p_gongdi", "p_duanzong", "sibling_of", None, None, None, None, "兄弟"),
    ("p_duanzong", "p_dibing", "succeeded_by", 1278, 5, 1279, 3, None),

    # 北宋开国集团
    ("p_zhaopu", "p_zhaokuangyin", "served_under", 956, None, 976, 11, None),
    ("p_zhaopu", "k_beisong", "founded", 960, 2, None, None, "谋主"),
    ("p_zhaokuangyin", "f_yishe_shixiongdi", "leader_of", 950, None, 976, 11, None),
    ("p_shishouxin_song", "f_yishe_shixiongdi", "member_of", 950, None, None, None, None),
    ("p_zhaokuangyin", "e_beijiu_shibingquan", "participated_in", 961, 7, None, None, "主导"),
    ("p_shishouxin_song", "e_beijiu_shibingquan", "participated_in", 961, 7, None, None, None),

    # 王安石变法 / 党争
    ("p_shenzong", "e_xining_bianfa", "participated_in", 1069, 2, 1085, 3, "主导"),
    ("p_wanganshi", "e_xining_bianfa", "participated_in", 1069, 2, 1076, None, "主持"),
    ("p_wanganshi", "p_shenzong", "served_under", 1069, None, 1085, 3, "宰相"),
    ("p_wanganshi", "f_xin_jiu_dang", "leader_of", 1069, None, None, None, "新党"),
    ("p_sima_guang", "f_xin_jiu_dang", "member_of", 1069, None, 1086, None, "旧党"),
    ("p_sima_guang", "f_yuanyou_dangren", "leader_of", 1086, None, 1086, None, None),
    ("p_sushi_song", "f_yuanyou_dangren", "member_of", 1086, None, 1101, 8, None),
    ("p_sushi_song", "f_xin_jiu_dang", "member_of", 1069, None, 1101, 8, "中立偏旧"),
    ("p_wanganshi", "p_sima_guang", "rival_of", 1069, None, 1086, None, "新旧党争"),
    ("p_caijing", "f_xin_jiu_dang", "member_of", 1102, None, 1126, 8, "借新法之名"),
    ("p_caijing", "e_yuanyou_dangbei", "participated_in", 1102, None, None, None, "主导"),
    ("p_huizong", "p_caijing", "served_under", 1102, None, 1125, 12, "四度相"),
    ("p_huizong", "p_tongguan", "served_under", None, None, 1125, 12, None),

    # 理学派
    ("p_zhoudunyi", "f_daoxue_pai", "member_of", 1030, None, 1073, 7, "开山"),
    ("p_chengyi", "f_daoxue_pai", "leader_of", 1050, None, 1107, 9, None),
    ("p_chenghao", "p_chengyi", "sibling_of", None, None, None, None, "兄弟"),
    ("p_zhuxi", "f_daoxue_pai", "leader_of", 1160, None, 1200, 4, "集大成"),
    ("p_zhuxi", "p_chengyi", "mentored_by", None, None, None, None, "程朱理学间接师承"),
    ("p_zhuxi", "p_lujiuyuan", "rival_of", 1175, None, None, None, "鹅湖之辩"),
    ("p_zhangzai", "f_daoxue_pai", "member_of", 1040, None, 1077, 12, "关学"),
    ("p_lujiuyuan", "f_daoxue_pai", "member_of", 1170, None, 1193, 1, "心学"),

    # 三苏 + 欧阳修
    ("p_suxun_song", "p_sushi_song", "father_of", 1037, 1, None, None, None),
    ("p_suxun_song", "p_suzhe", "father_of", 1039, None, None, None, None),
    ("p_sushi_song", "p_suzhe", "sibling_of", None, None, None, None, "兄弟"),
    ("p_ouyangxiu", "p_sushi_song", "mentored_by", 1057, None, None, None, "嘉祐二年主考"),

    # 寇准 / 澶渊
    ("p_kouzhun", "p_zhenzong", "served_under", 1004, None, 1022, 2, None),
    ("p_kouzhun", "e_chanyuan_zhimeng", "participated_in", 1004, None, 1005, 1, "力主亲征"),
    ("p_zhenzong", "e_chanyuan_zhimeng", "participated_in", 1004, None, None, None, "亲征"),
    ("p_xiaotaihou", "e_chanyuan_zhimeng", "participated_in", 1004, None, None, None, "亲征"),
    ("p_yelulongxu", "e_chanyuan_zhimeng", "participated_in", 1004, None, None, None, None),

    # 范仲淹/韩琦/包拯
    ("p_fanzhongyan", "e_qingli_xinzheng", "participated_in", 1043, None, 1045, None, "主持"),
    ("p_fanzhongyan", "p_renzong", "served_under", 1040, None, 1052, 6, None),
    ("p_hanqi", "p_renzong", "served_under", None, None, 1075, 8, None),
    ("p_baozheng", "p_renzong", "served_under", None, None, 1062, 5, None),

    # 宋夏
    ("p_liyuanhao", "k_xixia", "founded", 1038, 10, None, None, None),
    ("p_lijiqian", "p_lideming", "father_of", 981, None, None, None, None),
    ("p_lideming", "p_liyuanhao", "father_of", 1003, None, None, None, None),
    ("p_liyuanhao", "e_qingli_hexi", "participated_in", 1044, None, None, None, None),
    ("p_liyuanhao", "b_sanchuankou", "led", 1040, None, None, None, None),
    ("p_liyuanhao", "b_haoshuigu", "led", 1041, 3, None, None, None),

    # 靖康前后
    ("p_huizong", "e_haishang_zhimeng", "participated_in", 1120, None, None, None, "联金灭辽"),
    ("p_tongguan", "e_haishang_zhimeng", "participated_in", 1120, None, None, None, None),
    ("p_ligang_song", "e_jingkang_zhibian", "participated_in", 1126, None, None, None, "开封保卫战"),
    ("p_qinzong", "e_jingkang_zhibian", "participated_in", 1127, 3, None, None, None),
    ("p_huizong", "e_jingkang_zhibian", "participated_in", 1127, 3, None, None, None),
    ("p_zhangbangchang", "k_jin_jurchen", "served_under", 1127, None, 1127, 11, "大楚傀儡"),
    ("p_zhangbangchang", "e_jingkang_zhibian", "participated_in", 1127, 3, None, None, None),

    # 南宋抗金
    ("p_gaozong", "k_nansong", "founded", 1127, 5, None, None, None),
    ("p_gaozong", "e_jianyan_nandu", "participated_in", 1127, 5, None, None, None),
    ("p_zongze", "p_gaozong", "served_under", 1127, None, 1128, 7, None),
    ("p_yuefei", "p_gaozong", "served_under", 1127, None, 1142, 1, None),
    ("p_hanshizhong", "p_gaozong", "served_under", 1127, None, 1151, 9, None),
    ("p_yuefei", "b_yancheng", "led", 1140, 7, None, None, None),
    ("p_hanshizhong", "b_huangtiandang", "led", 1130, 4, None, None, None),
    ("p_lianghongyu", "b_huangtiandang", "participated_in", 1130, 4, None, None, "击鼓"),
    ("p_qinkuai", "p_gaozong", "served_under", 1131, None, 1155, 11, None),
    ("p_qinkuai", "p_yuefei", "killed", 1142, 1, None, None, "莫须有"),
    ("p_qinkuai", "e_shaoxing_heyi", "participated_in", 1141, 11, None, None, "主持"),
    ("p_gaozong", "e_shaoxing_heyi", "participated_in", 1141, 11, None, None, None),
    ("p_yuefei", "f_zhuzhan_touxiang", "leader_of", 1127, None, 1142, 1, "主战派"),
    ("p_qinkuai", "f_zhuzhan_touxiang", "member_of", 1131, None, 1155, 11, "投降派首领"),

    # 南宋后期
    ("p_jiasidao", "p_lizong", "served_under", 1259, None, 1275, 8, None),
    ("p_jiasidao", "p_duzong", "served_under", 1264, None, 1274, 8, None),
    ("p_luxiufu", "p_dibing", "killed", 1279, 3, None, None, "负帝投海"),
    ("p_zhangshijie", "p_dibing", "served_under", 1276, None, 1279, 3, None),
    ("p_wentianxiang", "p_gongdi", "served_under", 1275, None, 1278, None, None),
    ("p_luxiufu", "b_yashan", "participated_in", 1279, 3, None, None, None),
    ("p_zhangshijie", "b_yashan", "participated_in", 1279, 3, None, None, None),
    ("p_dibing", "b_yashan", "participated_in", 1279, 3, None, None, None),

    # 蒙古/元
    ("p_chengjisihan", "p_kuotai", "father_of", 1186, None, None, None, None),
    ("p_chengjisihan", "p_tuolei", "father_of", 1193, None, None, None, None),
    ("p_kuotai", "p_chengjisihan", "succeeded_by", 1229, None, None, None, None),
    ("p_mengge", "p_tuolei", "father_of", None, None, None, None, None) if False else
    ("p_tuolei", "p_mengge", "father_of", 1209, None, None, None, None),
    ("p_hubilai", "p_tuolei", "father_of", None, None, None, None, None) if False else
    ("p_tuolei", "p_hubilai", "father_of", 1215, None, None, None, None),
    ("p_mengge", "p_kuotai", "succeeded_by", 1251, None, None, None, None),
    ("p_yeluchucai", "p_chengjisihan", "served_under", 1218, None, 1227, 8, None),
    ("p_yeluchucai", "p_kuotai", "served_under", 1229, None, 1241, 12, None),

    # 金
    ("p_wanyanaguda", "k_jin_jurchen", "founded", 1115, 1, None, None, None),
    ("p_wanyanwuqimai", "p_wanyanaguda", "sibling_of", None, None, None, None, "弟"),
    ("p_wanyanwuqimai", "p_wanyanaguda", "succeeded_by", 1123, 9, None, None, None),
    ("p_wanyanliang", "p_wanyanyong", "succeeded_by", 1161, 12, None, None, "兵变自立"),
    ("p_wanyanwuzhu", "p_wanyanaguda", "father_of", None, None, None, None, "第四子"),
    ("p_wanyanwuzhu", "b_huangtiandang", "led", 1130, 4, None, None, None),
    ("p_wanyanwuzhu", "b_yancheng", "led", 1140, 7, None, None, "败"),
    ("p_wanyanshouxu", "b_caizhou_jinmie", "participated_in", 1234, 2, None, None, "自缢"),

    # 政权更替
    ("k_beisong", "k_jin_jurchen", "destroyed_by", 1127, 3, None, None, None),
    ("k_nansong", "d_yuan", "destroyed_by", 1279, 3, None, None, None),
    ("k_jin_jurchen", "d_yuan", "destroyed_by", 1234, 2, None, None, None),
    ("k_beisong", "k_nansong", "succeeded_by", 1127, 5, None, None, None),
    ("d_song", "k_beisong", "includes", 960, 2, 1127, 3, None),
    ("d_song", "k_nansong", "includes", 1127, 5, 1279, 2, None),

    # 因果链
    ("e_chenqiao", "e_beijiu_shibingquan", "preceded_by", None, None, None, None, "陈桥→释兵权"),
    ("e_chanyuan_zhimeng", "e_haishang_zhimeng", "preceded_by", None, None, None, None, "宋辽和平→海上之盟背辽"),
    ("e_haishang_zhimeng", "e_jingkang_zhibian", "preceded_by", None, None, None, None, "联金灭辽→靖康之变"),
    ("e_jingkang_zhibian", "e_jianyan_nandu", "preceded_by", None, None, None, None, "靖康→南渡"),
    ("e_xining_bianfa", "e_yuanyou_dangzheng_song", "preceded_by", None, None, None, None, "变法→党争"),
    ("e_lianmeng_miejin", "e_yashan_zhibian", "preceded_by", None, None, None, None, "联蒙灭金→宋蒙战争→崖山"),
    ("e_qingli_xinzheng", "e_xining_bianfa", "preceded_by", None, None, None, None, "庆历新政→王安石变法"),
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
    out = DATA / "relations" / "song.yaml"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(deduped, f, allow_unicode=True, sort_keys=False)
    print(f"  ✓ {len(deduped)} relations → data/relations/song.yaml")


if __name__ == "__main__":
    print(f"→ Phase 13: Song Dynasty (960-1279)")
    gen_places()
    print(f"  ✓ {len(PLACES)} places")
    gen_polities()
    print(f"  ✓ {len(POLITIES)} polities")
    gen_persons()
    print(f"  ✓ {len(PERSONS)} persons")
    gen_factions()
    print(f"  ✓ {len(FACTIONS)} factions")
    gen_battles()
    print(f"  ✓ {len(BATTLES)} battles")
    gen_events()
    print(f"  ✓ {len(EVENTS)} events")
    gen_relations()
    print("Done.")
