#!/usr/bin/env python3
"""Phase 12 — Qin + Han (BC 221 - 220).

Coverage:
- 战国末 / 秦(BC 259-206):秦灭六国、焚书坑儒、大泽乡起义、楚汉战争
- 西汉(BC 202-9):高祖、文景、武帝、昭宣、王莽篡汉
- 新(9-23):王莽改制、绿林赤眉
- 东汉(25-220):光武中兴、明章之治、班超通西域、宦官外戚、党锢、黄巾、董卓乱政
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
    ("pl_xianyang_qin", "咸阳", "咸阳", "陕西", 34.34, 108.71, "capital", [], "秦都"),
    ("pl_xian_qin", "新郑/郑", "新郑", "河南", 34.40, 113.86, "city", [], "韩都"),
    ("pl_handan_qin", "邯郸", "邯郸", "河北", 36.61, 114.54, "capital", [], "赵都"),
    ("pl_jimo_qin", "即墨", "平度", "山东", 36.88, 119.97, "city", [], "齐地"),
    ("pl_linzi_qin", "临淄", "淄博", "山东", 36.81, 118.31, "city", [], "齐都"),
    ("pl_shouchun_qin", "寿春", "寿县", "安徽", 32.57, 116.78, "capital", [], "楚末都"),
    ("pl_ying_qin", "郢/江陵", "荆州", "湖北", 30.33, 112.24, "capital", [], "楚旧都"),
    ("pl_jingxing", "井陉", "井陉", "河北", 38.13, 114.14, "battlefield", [], "韩信破赵"),
    ("pl_julu_qin", "巨鹿", "平乡", "河北", 37.07, 114.96, "battlefield", [], "BC207 巨鹿之战"),
    ("pl_changshan", "常山", "正定", "河北", 38.15, 114.57, "city", [], "赵佗封地"),
    ("pl_penglai", "蓬莱", "蓬莱", "山东", 37.81, 120.76, "city", [], "徐福出海"),
    ("pl_linjin", "临晋", "大荔", "陕西", 34.80, 109.94, "city", [], "黄河渡口"),
    ("pl_daze_xiang", "大泽乡", "宿州", "安徽", 33.64, 116.95, "battlefield", [], "BC209 大泽乡起义"),
    ("pl_pengcheng_han", "彭城", "徐州", "江苏", 34.26, 117.18, "city", [], "项羽都"),
    ("pl_xingyang_han", "荥阳", "荥阳", "河南", 34.79, 113.39, "battlefield", [], "楚汉争夺"),
    ("pl_chenggao", "成皋", "荥阳", "河南", 34.86, 113.39, "battlefield", [], "楚汉"),
    ("pl_gaixia", "垓下", "灵璧", "安徽", 33.50, 117.42, "battlefield", [], "BC202 垓下之战"),
    ("pl_wujiang", "乌江", "和县", "安徽", 31.74, 118.49, "city", [], "项羽自刎地"),
    ("pl_chang_an_han", "长安", "西安", "陕西", 34.27, 108.95, "capital", [], "西汉都"),
    ("pl_luoyang_han_east", "洛阳", "洛阳", "河南", 34.62, 112.45, "capital", [], "东汉都"),
    ("pl_yangping_pass", "阳平关", "宁强", "陕西", 32.83, 105.91, "garrison", [], "蜀道"),
    ("pl_ma_yi", "马邑", "朔州", "山西", 39.32, 112.43, "battlefield", [], "BC133 马邑之谋"),
    ("pl_mobei", "漠北", "外蒙古", "蒙古", 47.92, 106.92, "battlefield", [], "BC119 漠北之战"),
    ("pl_qilian", "祁连山", "祁连", "甘肃", 38.18, 100.25, "battlefield", [], "霍去病征匈奴"),
    ("pl_hexi_corridor", "河西走廊", "武威", "甘肃", 37.93, 102.64, "city", [], "河西四郡"),
    ("pl_dawan", "大宛", "费尔干纳", "乌兹别克斯坦", 40.99, 71.00, "city", [], "汉攻大宛,汗血马"),
    ("pl_kangju", "康居", "撒马尔罕", "乌兹别克斯坦", 39.66, 66.97, "city", [], "西域"),
    ("pl_daxia", "大夏", "巴尔赫", "阿富汗", 36.77, 66.90, "city", [], "中亚"),
    ("pl_ze_zhong_xian", "涿县", "涿州", "河北", 39.49, 115.98, "city", [], "刘备祖籍"),
    ("pl_baideng", "白登山", "大同", "山西", 40.18, 113.32, "battlefield", [], "BC200 白登之围"),
    ("pl_julu_qi", "巨鹿/常山", "平乡", "河北", 37.07, 114.96, "battlefield", [], "BC207 巨鹿之战"),
    ("pl_kunyang", "昆阳", "叶县", "河南", 33.62, 113.36, "battlefield", [], "23 昆阳之战"),
    ("pl_chang_an_xin", "常安(新)", "西安", "陕西", 34.27, 108.95, "capital", [], "王莽改"),
    ("pl_yongan_han", "白帝城", "奉节", "重庆", 31.05, 109.46, "city", [], "公孙述"),
    ("pl_guangling", "广陵", "扬州", "江苏", 32.39, 119.42, "city", [], "东汉江淮"),
    ("pl_zhongmu", "官渡/中牟", "中牟", "河南", 34.34, 114.07, "battlefield", [], "200 官渡之战"),
]


def gen_places():
    for tup in PLACES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["史记", "汉书", "后汉书", "中国历史地图集"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


PERSONS = [
    # === 秦 ===
    ("p_ying_zheng", "嬴政", ["秦始皇", "始皇帝", "赵政"], None, (None, None), (210, 7), "pl_handan_qin",
     "秦朝建立者。BC247 即秦王位(13岁),BC238 亲政。BC230-221 十年灭韩、赵、魏、楚、燕、齐六国,完成统一。自称'始皇帝'。废分封,行郡县,统一文字、货币、度量衡、车轨。BC213 焚书,BC212 坑儒。BC214 修长城。BC221-210 在位。BC210 七月东巡途中病卒于沙丘。宦官赵高与李斯篡改遗诏,立胡亥为二世,赐死扶苏。",
     "中国历史上第一位完成统一的皇帝。",
     ["史记·秦始皇本纪", "资治通鉴·卷6-7"]),
    ("p_fusu", "扶苏", None, None, (None, None), (210, None), "pl_shang_jun",
     "秦始皇长子。BC212 因谏焚书坑儒被贬上郡监蒙恬军。BC210 始皇崩,赵高、李斯矫诏赐死扶苏,立胡亥。",
     ["史记·李斯列传", "资治通鉴·卷7"]),
    ("p_hu_hai", "胡亥", ["秦二世"], None, (None, None), (207, 9), "pl_xianyang_qin",
     "秦二世。始皇少子。BC210 即位,任赵高为郎中令。BC209 大泽乡起义爆发。BC207 为赵高逼杀。",
     ["史记·秦始皇本纪"]),
    ("p_zi_ying", "子婴", ["秦王子婴"], None, (None, None), (206, None), "pl_xianyang_qin",
     "秦末代君主。BC207 即位,称秦王(去帝号)。设计杀赵高。BC206 刘邦入关,降。后为项羽所杀。",
     ["史记·秦始皇本纪"]),
    ("p_lv_bu_wei", "吕不韦", ["吕子"], "子", (None, None), (235, None), "pl_puyang_lvbuwei",
     "秦国相邦。阳翟大贾。庄襄王(子楚)时任相,封文信侯。始皇初年尊为'仲父'。BC237 免相,BC235 饮鸩死。门客著《吕氏春秋》。",
     ["史记·吕不韦列传"]),
    ("p_li_si", "李斯", None, None, (None, None), (208, None), "pl_shang_cai_lisi",
     "秦相。楚上蔡人。荀子学生。BC237 上《谏逐客书》。BC221 任丞相,主废分封、行郡县、统一文字。BC210 与赵高矫诏立胡亥。BC208 为赵高诬陷谋反,腰斩于咸阳,夷三族。",
     ["史记·李斯列传", "资治通鉴·卷7"]),
    ("p_wang_jian", "王翦", None, None, (None, None), (None, None), "pl_pingyang_wangjian",
     "秦名将。BC229-228 灭赵,BC223 灭楚,BC222 灭燕。战国四大名将之一。",
     ["史记·白起王翦列传"]),
    ("p_meng_tian", "蒙恬", None, None, (None, None), (210, None), "pl_qi_mengtian",
     "秦名将。BC215 率三十万却匈奴,收河南地。修筑长城。BC210 始皇崩,胡亥矫诏赐死。",
     ["史记·蒙恬列传"]),
    ("p_zhao_gao", "赵高", None, None, (None, None), (207, 9), "pl_xianyang_qin",
     "秦宦官。BC210 始皇崩,与李斯矫诏立胡亥,赐死扶苏、蒙恬。BC207 逼杀二世,立子婴。子婴设计诛之。",
     ["史记·秦始皇本纪"]),
    ("p_zhang_han", "章邯", None, None, (None, None), (205, None), "pl_xianyang_qin",
     "秦末将领。BC209 率骊山刑徒大破周文军。BC208 杀项梁于定陶。BC207 投降项羽于巨鹿(殷墟)。BC205 三秦王之一,都废丘。BC205 为韩信所破,自杀。",
     ["史记·秦始皇本纪", "资治通鉴·卷9"]),

    # === 楚汉 ===
    ("p_xiang_yu", "项羽", ["项籍", "西楚霸王"], "羽", (232, None), (202, None), "pl_xiaxiang_xiangyu",
     "楚汉战争主要人物。下相人。项梁侄。BC209 起兵吴中。BC207 巨鹿之战破釜沉舟,大破秦军主力。BC206 入关,焚咸阳,自称西楚霸王,都彭城,分封十八路诸侯。BC205 与刘邦战。BC202 垓下之战为韩信所败,突围至乌江自刎。",
     "中国历史上最传奇的悲剧英雄。",
     ["史记·项羽本纪", "资治通鉴·卷8-11"]),
    ("p_xiang_liang", "项梁", None, None, (None, None), (208, None), "pl_xiaxiang_xiangyu",
     "项羽叔。BC209 起兵吴中。立楚怀王孙心。BC208 战死于定陶。",
     ["史记·项羽本纪"]),
    ("p_fan_zeng", "范增", ["范亚父"], None, (277, None), (204, None), "pl_chao_xian_fanzeng",
     "项羽谋士。'亚父'。BC208 劝项梁立楚怀王孙心。BC206 鸿门宴劝项羽杀刘邦。后离间而死。",
     ["史记·项羽本纪"]),
    ("p_liu_bang_qin", "刘邦", ["汉高祖", "沛公", "刘季"], None, (256, None), (195, 6), "pl_pei_xian_liubang",
     "汉朝建立者。沛县丰邑人,平民出身。BC209 沛县起兵,称沛公。BC206 入关灭秦,约法三章。BC206 被项羽封为汉王。BC205 还定三秦,楚汉战争爆发。BC202 垓下之战灭项羽,称帝建汉,都长安。BC202-195 在位。'汉承秦制',奠定汉朝。",
     "中国历史上第一位平民出身的开国皇帝。",
     ["史记·高祖本纪", "汉书·高帝纪"]),
    ("p_xiao_he", "萧何", None, None, (None, None), (193, None), "pl_pei_xian_xiaohe",
     "汉初三杰之一。沛人。'镇国家,抚百姓'。BC206 入咸阳收秦图书。BC202 任相国。BC196 与吕后诛韩信。",
     ["史记·萧相国世家"]),
    ("p_zhang_liang", "张良", ["张子房", "留侯"], "子房", (None, None), (189, None), "pl_chengliu_zhangliang",
     "汉初三杰之一。祖父五代相韩。'运筹帷幄之中,决胜千里之外'。BC218 博浪沙刺秦皇。BC209 从刘邦。BC206 鸿门宴救刘邦。BC202 垓下之战前劝刘邦封韩信为王。功成身退。",
     ["史记·留侯世家"]),
    ("p_han_xin", "韩信", ["韩重言", "淮阴侯", "齐王", "楚王"], "重言", (231, None), (196, None), "pl_huaiyin",
     "汉初三杰之一。淮阴人。'国士无双'。初投项梁、项羽,后归刘邦。BC206 拜大将军。'明修栈道,暗渡陈仓'。BC204 破赵,BC203 灭齐。BC202 垓下之战指挥全军灭项羽。BC201 贬淮阴侯。BC196 为吕后所杀。",
     "中国军事史'兵仙'。",
     ["史记·淮阴侯列传"]),
    ("p_caocan", "曹参", None, None, (None, None), (190, None), "pl_pei_xian_caocan",
     "汉初功臣。萧何后任相国。'萧规曹随'。",
     ["史记·曹相国世家"]),
    ("p_fan_kuai", "樊哙", None, None, (242, None), (189, None), "pl_pei_xian_fankuai",
     "汉初骁将。刘邦连襟(娶吕媭)。BC206 鸿门宴闯帐救刘邦。",
     ["史记·樊郦滕灌列传"]),
    ("p_chen_ping", "陈平", None, None, (None, None), (178, None), "pl_huyang_chenping",
     "汉初功臣。'六出奇计'。BC204 反间范增。BC200 白登之围贿赂阏氏解围。惠帝朝为相。",
     ["史记·陈丞相世家"]),

    # === 西汉皇帝 ===
    ("p_lv_zhi", "吕雉", ["吕后", "高后"], None, (241, None), (180, None), "pl_danfu_lvzhi",
     "汉高祖皇后。BC195 高祖崩,惠帝即位。BC188 惠帝崩,临朝称制 8 年。BC180 病卒。诸吕之乱被周勃、陈平所平。",
     "中国历史上第一位实际掌握最高权力的女性。",
     ["史记·吕太后本纪"]),
    ("p_liu_heng", "刘恒", ["汉文帝"], None, (203, None), (157, None), "pl_dai_liu_heng",
     "汉文帝。高祖第四子。BC180 周勃、陈平诛诸吕,迎立代王恒。BC180-157 在位。轻徭薄赋,与民休息。'文景之治'开启。",
     ["史记·孝文本纪"]),
    ("p_liu_qi", "刘启", ["汉景帝"], None, (188, None), (141, None), "pl_chang_an_han",
     "汉景帝。文帝子。BC157-141 在位。BC154 七国之乱,周亚夫平之。'文景之治'完成。",
     ["史记·孝景本纪"]),
    ("p_liu_che", "刘彻", ["汉武帝"], None, (156, None), (87, None), "pl_chang_an_han",
     "汉武帝。景帝子。BC141-87 在位。BC140 改元建元(始用年号)。BC134 察举制。BC127 推恩令。BC121 霍去病破匈奴,取河西。BC119 卫青、霍去病漠北之战大破匈奴。BC138/BC119 张骞通西域。BC91 巫蛊之祸,太子据自杀。BC87 崩。",
     "中国历史上最伟大的帝王之一,开启汉朝鼎盛。",
     ["史记·孝武本纪", "汉书·武帝纪"]),
    ("p_liu_fuling", "刘弗陵", ["汉昭帝"], None, (94, None), (74, None), "pl_chang_an_han",
     "汉昭帝。武帝少子。BC87-74 在位。霍光辅政。BC81 盐铁会议。",
     ["汉书·昭帝纪"]),
    ("p_liu_xun", "刘询", ["汉宣帝", "刘病已"], None, (91, None), (49, None), "pl_chang_an_han",
     "汉宣帝。武帝曾孙,戾太子刘据孙。BC74-49 在位。霍光辅政至 BC66。'昭宣中兴'。",
     ["汉书·宣帝纪"]),
    ("p_liu_ao", "刘骜", ["汉成帝"], None, (51, None), (7, None), "pl_chang_an_han",
     "汉成帝。BC33-7 在位。宠赵飞燕、赵合德。外戚王氏专权。",
     ["汉书·成帝纪"]),
    ("p_zhao_feiyan", "赵飞燕", ["赵皇后", "孝成赵皇后"], None, (None, None), (1, None), "pl_wu_yang_zhaofeiyan",
     "汉成帝皇后。原阳阿公主家舞女。'环肥燕瘦'。",
     ["汉书·外戚传"]),
    ("p_wang_mang", "王莽", ["王巨君", "建兴帝"], "巨君", (45, None), (23, 10), "pl_chang_an_xin",
     "新朝建立者。魏郡元城人,汉元帝王皇后之侄。BC1 任大司马。AD6 摄政(居摄)。AD9 受孺子婴禅让,改国号'新'。推行托古改制(王田私属、五均六筦)。改官名、地名。失败,引发赤眉绿林起义。AD23 为商人杜吴所杀,新亡。",
     "中国历史上争议最大的篡位者。",
     ["汉书·王莽传", "资治通鉴·卷36-39"]),

    # === 西汉将相 ===
    ("p_wei_qing", "卫青", ["卫仲卿"], "仲卿", (None, None), (106, None), "pl_pingyang_weiqing",
     "西汉名将。卫子夫弟。BC129-119 五次出击匈奴。BC127 收复河南地,BC119 漠北之战大破匈奴,封长平侯。",
     ["史记·卫将军骠骑列传"]),
    ("p_huo_qubing", "霍去病", None, None, (140, None), (117, None), "pl_pingyang_huoqubing",
     "西汉名将。卫青外甥。BC121 二次征河西,降匈奴休屠王、浑邪王,取河西四郡(武威、张掖、酒泉、敦煌)。BC119 漠北之战封狼居胥。BC117 病卒,年24。'匈奴未灭,何以家为'。",
     "中国军事史上最辉煌的青年统帅。",
     ["史记·卫将军骠骑列传"]),
    ("p_li_guang", "李广", ["李飞将军", "飞将军"], None, (None, None), (119, None), "pl_longxi_liguang",
     "西汉名将。陇西成纪人。历仕文、景、武三朝,与匈奴七十余战。BC119 随卫青漠北之战失道,自杀。'李广难封'。",
     ["史记·李将军列传"]),
    ("p_zhang_qian", "张骞", ["张博望"], None, (None, None), (114, None), "pl_hanzhong_zhangqian",
     "西汉外交家。汉中人。BC138 武帝派其出使大月氏,欲联合夹击匈奴。被匈奴扣留 10 年。BC126 还朝。BC119 二次出使乌孙。'凿空西域'。",
     "丝绸之路的开拓者。",
     ["史记·大宛列传", "汉书·张骞传"]),
    ("p_su_wu", "苏武", ["苏子卿"], "子卿", (140, None), (60, None), "pl_du_liu_suwu",
     "西汉名臣。BC100 出使匈奴被扣留,牧羊北海(贝加尔湖)19 年,持节不屈。BC81 还朝。",
     "中国忠贞不屈的象征。",
     ["汉书·苏武传"]),
    ("p_huo_guang", "霍光", ["霍子孟"], "子孟", (None, None), (68, None), "pl_hedong_huoguang",
     "西汉权臣。霍去病弟。BC87 武帝临终托孤辅昭帝。BC74 废昌邑王刘贺,立宣帝。历昭、宣两朝,执政 20 年。",
     ["汉书·霍光金日磾传"]),
    ("p_dong_zhongshu", "董仲舒", None, None, (179, None), (104, None), "pl_guangchuan_dongzhongshu",
     "西汉思想家。BC134 提出'罢黜百家,独尊儒术'。'天人三策'。著《春秋繁露》。",
     "儒学成为中国正统的关键人物。",
     ["汉书·董仲舒传"]),
    ("p_sima_qian", "司马迁", ["司马子长"], "子长", (145, None), (86, None), "pl_longmen_simaqian",
     "西汉史学家、文学家。BC108 任太史令。BC104 开始撰《史记》。BC99 因李陵事件受宫刑。BC91 完成《史记》。'究天人之际,通古今之变,成一家之言'。",
     "中国史学之父。",
     ["史记·太史公自序", "汉书·司马迁传"]),

    # === 东汉 ===
    ("p_liu_xiu", "刘秀", ["汉光武帝"], None, (5, None), (57, 3), "pl_caiyang_liuxiu",
     "东汉建立者。刘邦九世孙。22 起兵反新莽。23 昆阳之战以 8000 破王莽 42 万(天文陨石助之)。25 称帝,建元建武,都洛阳。25-57 在位,平定群雄,统一全国。'光武中兴'。",
     "中国历史上'允冠百王'。",
     ["后汉书·光武帝纪", "资治通鉴·卷38-44"]),
    ("p_liu_zhuang_dong", "刘庄", ["汉明帝"], None, (28, None), (75, None), "pl_luoyang_han_east",
     "汉明帝。58-75 在位。永平之治。佛教入华(白马寺)。",
     ["后汉书·明帝纪"]),
    ("p_liu_da_dong", "刘炟", ["汉章帝"], None, (57, None), (88, None), "pl_luoyang_han_east",
     "汉章帝。76-88 在位。'明章之治'。79 白虎观会议。",
     ["后汉书·章帝纪"]),
    ("p_ban_chao", "班超", ["班仲升"], "仲升", (32, None), (102, None), "pl_pingling_banchao",
     "东汉名将、外交家。班彪子,班固弟。73 出使西域。'投笔从戎'。74-102 在西域 31 年,以夷制夷,平定西域五十余国。封定远侯。102 年 70 岁还洛阳,九月卒。",
     "经营西域的杰出统帅。",
     ["后汉书·班超传"]),
    ("p_ban_gu", "班固", ["班孟坚"], "孟坚", (32, None), (92, None), "pl_pingling_banchao",
     "东汉史学家。班彪子。著《汉书》,中国第一部纪传体断代史。",
     ["后汉书·班固传"]),
    ("p_ma_yuan_dong", "马援", ["马文渊", "伏波将军"], "文渊", (14, None), (49, None), "pl_maocheng_mayuan",
     "东汉名将。'伏波将军'。平定交趾。'男儿要当死于边野,以马革裹尸还葬耳'。",
     ["后汉书·马援传"]),
    ("p_dou_xian", "窦宪", ["窦伯度"], "伯度", (None, None), (92, None), "pl_xianyang_qin",
     "东汉外戚、名将。89 大破北匈奴于金微山,登燕然山刻石。91 灭北匈奴。92 因谋反赐死。",
     ["后汉书·窦宪传"]),
    ("p_zhang_heng", "张衡", ["张平子"], "平子", (78, None), (139, None), "pl_nanyang_zhangheng",
     "东汉科学家、文学家。发明浑天仪、地动仪。著《二京赋》《归田赋》。",
     ["后汉书·张衡传"]),
    ("p_cai_lun", "蔡伦", None, None, (62, None), (121, None), "pl_guiyang_cailun",
     "东汉宦官。改进造纸术(105)。后汉蔡侯纸。",
     "中国四大发明之一造纸术的关键改进者。",
     ["后汉书·宦者传·蔡伦"]),

    # === 黄巾起义 + 三国前夕 ===
    ("p_zhang_jiao", "张角", ["张天师", "大贤良师"], None, (None, None), (184, 9), "pl_ju_lu_zhangjiao",
     "黄巾起义领袖。巨鹿人。太平道创立者。184 二月率徒众数十万起兵,自称'天公将军',弟宝、梁称'地公将军'、'人公将军'。同年病死,起义失败。",
     ["后汉书·皇甫嵩传"]),
    ("p_zhang_bao", "张宝", ["地公将军"], None, (None, None), (184, None), "pl_ju_lu_zhangjiao",
     "黄巾起义首领。张角次弟。184 战死于下曲阳。",
     ["后汉书·皇甫嵩传"]),

    # === 三国前夕群雄 ===
    ("p_dong_zhuo", "董卓", ["董仲颖"], "仲颖", (None, None), (192, 5), "pl_lintao_dongzhuo",
     "东汉末权臣。陇西临洮人,凉州军阀。189 入洛阳,废少帝,立献帝,自任太师,残暴。190 关东诸侯讨之,挟献帝迁都长安,焚洛阳。192 为司徒王允与吕布所杀。",
     "汉末军阀混战的开启者。",
     ["后汉书·董卓传", "三国志·魏书·董卓传"]),
    ("p_lv_bu", "吕布", ["吕奉先"], "奉先", (None, None), (199, 2), "pl_jiuyuan_lvbu",
     "汉末骁将。五原九原人。先从丁原,杀丁原投董卓,与王允杀董卓。后投袁绍、张杨、刘备。198 为曹操所擒,白门楼缢杀。",
     "'三姓家奴'。",
     ["后汉书·吕布传", "三国志·魏书·吕布传"]),
    ("p_yuan_shao", "袁绍", ["袁本初"], "本初", (None, None), (202, 5), "pl_ruyang_yuanshao",
     "汉末群雄之一。汝南汝阳人。'四世三公'。190 关东联军盟主讨董卓。199 灭公孙瓒,据有冀、青、幽、并四州。200 官渡之战大败于曹操。202 病卒。",
     ["三国志·魏书·袁绍传"]),
]
PERSONS = [p for p in PERSONS if p is not None and not p[0].endswith(("_existing", "_add", "_pre"))]


# Birthplaces
EXTRA_BIRTH = [
    ("pl_shang_jun", "上郡", "榆林", "陕西", 38.30, 109.78, "garrison", [], "扶苏监军地"),
    ("pl_puyang_lvbuwei", "濮阳", "濮阳", "河南", 35.76, 115.03, "birthplace", [], "吕不韦籍贯"),
    ("pl_shang_cai_lisi", "上蔡", "上蔡", "河南", 33.26, 114.26, "birthplace", [], "李斯籍贯"),
    ("pl_pingyang_wangjian", "频阳", "富平", "陕西", 34.78, 109.18, "birthplace", [], "王翦籍贯"),
    ("pl_qi_mengtian", "琅琊/蒙阴", "蒙阴", "山东", 35.71, 117.95, "birthplace", [], "蒙恬籍贯"),
    ("pl_xiaxiang_xiangyu", "下相", "宿迁", "江苏", 33.96, 118.28, "birthplace", [], "项羽籍贯"),
    ("pl_chao_xian_fanzeng", "居巢", "巢湖", "安徽", 31.60, 117.87, "birthplace", [], "范增籍贯"),
    ("pl_pei_xian_liubang", "沛县", "沛县", "江苏", 34.73, 116.94, "birthplace", [], "刘邦籍贯"),
    ("pl_pei_xian_xiaohe", "沛县", "沛县", "江苏", 34.73, 116.94, "birthplace", [], "萧何籍贯"),
    ("pl_chengliu_zhangliang", "城父", "宝丰", "河南", 33.86, 113.06, "birthplace", [], "张良籍贯"),
    ("pl_pei_xian_caocan", "沛县", "沛县", "江苏", 34.73, 116.94, "birthplace", [], "曹参籍贯"),
    ("pl_pei_xian_fankuai", "沛县", "沛县", "江苏", 34.73, 116.94, "birthplace", [], "樊哙籍贯"),
    ("pl_huyang_chenping", "户牖/阳武", "兰考", "河南", 34.82, 114.83, "birthplace", [], "陈平籍贯"),
    ("pl_danfu_lvzhi", "单父", "单县", "山东", 34.80, 116.10, "birthplace", [], "吕雉籍贯"),
    ("pl_dai_liu_heng", "代地", "太原", "山西", 37.77, 112.55, "city", [], "刘恒初封代王"),
    ("pl_wu_yang_zhaofeiyan", "吴/长安", "苏州/西安", "江苏", 31.30, 120.62, "birthplace", [], "赵飞燕"),
    ("pl_chang_an_xin", "常安", "西安", "陕西", 34.27, 108.95, "capital", [], "王莽改"),
    ("pl_pingyang_weiqing", "平阳", "临汾", "山西", 36.07, 111.52, "birthplace", [], "卫青籍贯"),
    ("pl_pingyang_huoqubing", "平阳", "临汾", "山西", 36.07, 111.52, "birthplace", [], "霍去病籍贯"),
    ("pl_longxi_liguang", "陇西成纪", "秦安", "甘肃", 34.86, 105.66, "birthplace", [], "李广籍贯"),
    ("pl_hanzhong_zhangqian", "汉中成固", "城固", "陕西", 33.16, 107.46, "birthplace", [], "张骞籍贯"),
    ("pl_du_liu_suwu", "杜陵", "西安", "陕西", 34.16, 108.96, "birthplace", [], "苏武籍贯"),
    ("pl_hedong_huoguang", "河东平阳", "临汾", "山西", 36.07, 111.52, "birthplace", [], "霍光籍贯"),
    ("pl_guangchuan_dongzhongshu", "广川", "景县", "河北", 37.69, 116.27, "birthplace", [], "董仲舒籍贯"),
    ("pl_longmen_simaqian", "龙门", "韩城", "陕西", 35.47, 110.43, "birthplace", [], "司马迁籍贯"),
    ("pl_caiyang_liuxiu", "蔡阳/舂陵", "枣阳", "湖北", 32.13, 112.76, "birthplace", [], "刘秀籍贯"),
    ("pl_pingling_banchao", "平陵/扶风", "咸阳/兴平", "陕西", 34.33, 108.49, "birthplace", [], "班超籍贯"),
    ("pl_maocheng_mayuan", "茂陵/扶风", "兴平", "陕西", 34.30, 108.49, "birthplace", [], "马援籍贯"),
    ("pl_nanyang_zhangheng", "南阳西鄂", "南阳", "河南", 32.99, 112.53, "birthplace", [], "张衡籍贯"),
    ("pl_guiyang_cailun", "桂阳/耒阳", "耒阳", "湖南", 26.41, 112.86, "birthplace", [], "蔡伦籍贯"),
    ("pl_ju_lu_zhangjiao", "巨鹿", "巨鹿", "河北", 37.07, 114.96, "birthplace", [], "张角籍贯"),
    ("pl_lintao_dongzhuo", "临洮", "临洮", "甘肃", 35.37, 103.86, "birthplace", [], "董卓籍贯"),
    ("pl_jiuyuan_lvbu", "九原", "包头", "内蒙古", 40.66, 109.84, "birthplace", [], "吕布籍贯"),
    ("pl_ruyang_yuanshao", "汝阳", "商水", "河南", 33.53, 114.30, "birthplace", [], "袁绍籍贯"),
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
        if pid in ("p_lv_zhi", "p_zhao_feiyan"):
            obj["gender"] = "female"
        if birthplace:
            obj["birthplace"] = birthplace
        obj["bio"] = bio
        if significance:
            obj["ext"] = {"significance": significance}
        obj["sources"] = srcs
        write(DATA / "entities" / "persons" / f"{pid[2:]}.yaml", obj)


def gen_birthplaces():
    for tup in EXTRA_BIRTH:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["史记", "汉书", "后汉书", "中国历史地图集"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


POLITIES = [
    ("k_qin", "秦朝", "Qin", "#c0392b", (None, None), (207, None), "p_ying_zheng", "pl_xianyang_qin", None, "k_xihan",
     "中国第一个大一统帝国。BC221 秦始皇完成统一,BC207 子婴降刘邦。",
     "史记·秦始皇本纪;汉书"),
    ("k_chu_xiang", "西楚", "Xi Chu", "#8e44ad", (206, 2), (202, None), "p_xiang_yu", "pl_pengcheng_han", None, "k_xihan",
     "项羽所建,仅四年。BC202 垓下之战为汉所灭。",
     "史记·项羽本纪"),
    ("k_xihan", "西汉", "Western Han", "#e74c3c", (202, 2), (9, 1), "p_liu_bang_qin", "pl_chang_an_han", "k_chu_xiang", "k_xin",
     "汉朝。刘邦建。BC141-87 武帝朝鼎盛。BC9 王莽篡汉。",
     "汉书"),
    ("k_xin", "新", "Xin", "#34495e", (9, None), (23, None), "p_wang_mang", "pl_chang_an_xin", "k_xihan", "k_donghan",
     "王莽所建。改制失败,23 年为绿林军所灭。",
     "汉书·王莽传"),
    ("k_donghan", "东汉", "Eastern Han", "#f39c12", (25, None), (220, 12), "p_liu_xiu", "pl_luoyang_han_east", "k_xin", "k_caowei",
     "刘秀建。220 曹丕代汉,东汉亡,三国开始。",
     "后汉书"),
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


EVENTS = [
    ("e_qin_mie_liuguo", "秦灭六国", (None, None), (221, None), "institution", "pl_xianyang_qin", ["k_qin"],
     "BC230-221 秦王政发动统一战争,十年间灭韩(230)、赵(228)、魏(225)、楚(223)、燕(222)、齐(221)。",
     "中国历史上第一次完成统一。",
     ["史记·秦始皇本纪", "资治通鉴·卷6-7"]),
    ("e_fenshu_kengru", "焚书坑儒", (213, None), None, "institution", "pl_xianyang_qin", ["k_qin"],
     "BC213 李斯建议焚毁民间所藏诗书百家语。BC212 坑杀犯禁者 460 余人于咸阳。",
     "中国文化史上重大事件。",
     ["史记·秦始皇本纪"]),
    ("e_daze_xiang_qiyi", "大泽乡起义", (209, 7), None, "institution", "pl_daze_xiang", ["k_qin"],
     "BC209 七月陈胜、吴广率戍卒 900 人在大泽乡起兵。'王侯将相,宁有种乎'。占领陈,立张楚政权。BC209 败。",
     "中国历史上第一次大规模农民起义。",
     ["史记·陈涉世家", "资治通鉴·卷7"]),
    ("e_julu_zhizhan", "巨鹿之战", (207, 12), None, "battle", "pl_julu_qin", ["k_chu_xiang", "k_qin"],
     "BC207 项羽率楚军 5 万,破釜沉舟,九战九捷,大破章邯、王离率领的秦军主力 40 万。王离被俘,章邯投降。",
     "秦朝覆灭的决定性战役。",
     ["史记·项羽本纪", "资治通鉴·卷8"]),
    ("e_chuhan_zhanzheng", "楚汉战争", (206, 8), (202, 12), "battle", "pl_xingyang_han", ["k_chu_xiang", "k_xihan"],
     "BC206 项羽封刘邦为汉王,都南郑。BC206 八月刘邦还定三秦。BC205-202 四年楚汉对峙,荥阳、成皋长期争夺。BC202 垓下之战,韩信指挥,灭项羽。",
     "刘邦战胜项羽,奠定汉朝。",
     ["史记·项羽本纪·高祖本纪", "资治通鉴·卷9-11"]),
    ("e_gaixia_zhizhan", "垓下之战", (202, 12), None, "battle", "pl_gaixia", ["k_chu_xiang", "k_xihan"],
     "BC202 十二月汉军 30 万围项羽于垓下(韩信为帅)。'四面楚歌',项羽率八百骑突围至乌江,自刎。",
     "汉朝建立前奏。",
     ["史记·项羽本纪", "资治通鉴·卷11"]),
    ("e_baideng_zhi_wei", "白登之围", (200, 12), None, "battle", "pl_baideng", ["k_xihan", "k_xiongnu"],
     "BC200 汉高祖率 32 万亲征匈奴冒顿单于 40 万骑,被围于平城白登山七日七夜。陈平贿赂阏氏解围。",
     "汉朝对匈奴转入和亲政策。",
     ["史记·匈奴列传", "资治通鉴·卷11"]),
    ("e_wen_jing_zhizhi", "文景之治", (180, None), (141, None), "reform", "pl_chang_an_han", ["k_xihan"],
     "BC180-141 文帝、景帝在位期间,轻徭薄赋,与民休息,黄老之治。国库充盈,粮仓腐烂。",
     "为武帝朝鼎盛奠定物质基础。",
     ["史记·孝文本纪、孝景本纪", "资治通鉴·卷13-16"]),
    ("e_qiguo_zhiluan", "七国之乱", (154, 1), (154, 3), "institution", "pl_chang_an_han", ["k_xihan"],
     "BC154 景帝采纳晁错削藩策,吴王刘濞联合楚、赵、胶东、胶西、菑川、济南六国叛乱。周亚夫三个月平定。",
     "中央集权关键一步,为武帝削藩奠定基础。",
     ["史记·吴王濞列传", "资治通鉴·卷15"]),
    ("e_tui_en_ling", "推恩令", (127, None), None, "institution", "pl_chang_an_han", ["k_xihan"],
     "BC127 武帝采主父偃策,令诸侯王分封子弟为列侯,使王国越分越小。",
     "兵不血刃解决诸侯王问题。",
     ["史记·平津侯主父列传", "汉书·武帝纪"]),
    ("e_mobei_zhizhan", "漠北之战", (119, None), None, "battle", "pl_mobei", ["k_xihan", "k_xiongnu"],
     "BC119 卫青、霍去病各率 5 万骑深入漠北。卫青破单于主力,霍去病封狼居胥,大破左贤王。匈奴远遁,漠南无王庭。",
     "汉匈百年战争汉朝最大胜利。",
     ["史记·匈奴列传", "资治通鉴·卷19"]),
    ("e_zhang_qian_xiyu", "张骞通西域", (138, None), (115, None), "diplomacy", "pl_hexi_corridor", ["k_xihan"],
     "BC138 张骞首次出使大月氏,BC126 还。BC119 二次出使乌孙。'凿空'西域。丝绸之路开启。",
     "东西方文明交流的开端。",
     ["史记·大宛列传", "资治通鉴·卷18"]),
    ("e_wugu_zhi_huo", "巫蛊之祸", (91, None), None, "coup", "pl_chang_an_han", ["k_xihan"],
     "BC91 江充诬陷太子刘据行巫蛊术诅咒武帝。太子起兵杀江充,兵败,母子皆自杀。死者数万。",
     "武帝晚年悲剧,后昭帝、宣帝继位。",
     ["汉书·江充传、武五子传", "资治通鉴·卷22"]),
    ("e_wang_mang_chuan_han", "王莽篡汉", (9, 1), None, "coup", "pl_chang_an_xin", ["k_xihan", "k_xin"],
     "AD9 王莽受孺子婴禅让,改国号新。推行托古改制(王田私属、五均六筦)。失败。",
     "中国历史上第一个'和平'篡位。",
     ["汉书·王莽传"]),
    ("e_wang_mang_gaige", "王莽改制", (9, None), (22, None), "reform", "pl_chang_an_xin", ["k_xin"],
     "9-22 王莽推行全面改制:王田制(土地国有)、私属(废除奴隶)、五均六筦(国家控制工商业)、改官名地名币制。",
     "脱离实际,引发大乱。新朝覆灭主因。",
     ["汉书·王莽传"]),
    ("e_lvlin_chimei", "绿林赤眉起义", (17, None), (27, None), "institution", "pl_changshan", ["k_xin", "k_xihan"],
     "17 王匡、王凤于绿林山起兵(绿林军)。18 樊崇于莒起兵(赤眉军)。23 绿林军立刘玄为更始帝。23 昆阳之战王莽主力被歼。25 刘秀称帝,27 灭赤眉。",
     "新朝覆灭,东汉建立。",
     ["后汉书·刘玄传、刘盆子传", "资治通鉴·卷38-41"]),
    ("e_kunyang_zhizhan", "昆阳之战", (23, 6), None, "battle", "pl_kunyang", ["k_xin", "k_xihan"],
     "23 年六月王莽遣王邑、王寻率 42 万大军围昆阳。刘秀率数千兵突围求援,内外夹击,会陨石坠营,新军大溃。'天助昆阳'。",
     "新朝覆灭决定性战役。",
     ["后汉书·光武帝纪", "资治通鉴·卷39"]),
    ("e_guangwu_zhongxing", "光武中兴", (25, None), (57, None), "reform", "pl_luoyang_han_east", ["k_donghan"],
     "25-57 光武帝刘秀在位。释放奴婢、减轻赋税、整顿吏治。统一全国(37)。",
     "东汉开始。",
     ["后汉书·光武帝纪"]),
    ("e_banchao_xiyu", "班超通西域", (73, None), (102, None), "diplomacy", "pl_hexi_corridor", ["k_donghan"],
     "73 班超率 36 人出使西域。74-102 在西域 31 年,以夷制夷,平定五十余国。东汉在西域设立都护府。",
     "汉朝重新控制西域。",
     ["后汉书·班超传"]),
    ("e_baihu_guan_huiyi", "白虎观会议", (79, None), None, "institution", "pl_luoyang_han_east", ["k_donghan"],
     "79 章帝召集群臣于白虎观讨论五经异同。班固记录为《白虎通义》。",
     "东汉经学集大成,儒家国教化。",
     ["后汉书·章帝纪"]),
    ("e_danggu_zhi_huo", "党锢之祸", (166, None), (184, None), "institution", "pl_luoyang_han_east", ["k_donghan"],
     "166-184 桓、灵二帝时,宦官专权。士大夫李膺、范滂等清流与宦官对抗。宦官以'党人'罪名禁锢百余人。184 黄巾起义后才赦免党人,但东汉已摇摇欲坠。",
     "东汉政治关键事件,反映士大夫与宦官的长期冲突。",
     ["后汉书·党锢传"]),
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


RELATIONS = [
    # 秦
    ("p_ying_zheng", "k_qin", "founded", None, None, None, None, "完成统一"),
    ("p_ying_zheng", "p_fusu", "father_of", None, None, None, None, None),
    ("p_ying_zheng", "p_hu_hai", "father_of", None, None, None, None, None),
    ("p_lv_bu_wei", "p_ying_zheng", "served_under", None, None, 235, None, "相邦"),
    ("p_li_si", "p_ying_zheng", "served_under", None, None, 208, None, "丞相"),
    ("p_zhao_gao", "p_hu_hai", "served_under", None, None, 207, 9, None),
    ("p_wang_jian", "p_ying_zheng", "served_under", None, None, None, None, "灭楚"),
    ("p_meng_tian", "p_ying_zheng", "served_under", None, None, 210, None, "却匈奴"),
    ("p_zhao_gao", "p_fusu", "killed", None, None, None, None, "矫诏赐死"),
    ("p_zhao_gao", "p_li_si", "killed", 208, None, None, None, "诬陷谋反"),
    ("p_zhao_gao", "p_hu_hai", "killed", 207, 9, None, None, "逼杀"),
    ("p_ying_zheng", "e_qin_mie_liuguo", "participated_in", None, None, None, None, "主导"),
    ("p_ying_zheng", "e_fenshu_kengru", "participated_in", 213, None, 210, 7, "主导"),
    ("p_zhang_han", "p_ying_zheng", "served_under", None, None, 209, None, None),
    ("p_zhang_han", "k_qin", "served_under", None, None, 207, None, None),

    # 楚汉
    ("p_xiang_liang", "p_xiang_yu", "uncle_of", None, None, None, None, "叔侄"),
    ("p_xiang_yu", "k_chu_xiang", "founded", 206, 2, None, None, "都彭城"),
    ("p_xiang_yu", "p_fan_zeng", "served_under", None, None, 204, None, "亚父"),
    ("p_xiang_yu", "e_julu_zhizhan", "led", 207, 12, None, None, "破釜沉舟"),
    ("p_xiang_yu", "e_chuhan_zhanzheng", "participated_in", 206, 8, 202, 12, None),
    ("p_xiang_yu", "e_gaixia_zhizhan", "led", 202, 12, None, None, "战败"),
    ("p_liu_bang_qin", "k_xihan", "founded", 202, 2, None, None, "都长安"),
    ("p_liu_bang_qin", "p_xiang_yu", "rival_of", 206, 8, 202, 12, "楚汉"),
    ("p_liu_bang_qin", "e_chuhan_zhanzheng", "led", 206, 8, 202, 12, None),
    ("p_liu_bang_qin", "e_gaixia_zhizhan", "led", 202, 12, None, None, "胜方"),
    ("p_liu_bang_qin", "p_xiao_he", "served_under", None, None, 195, 6, "相国"),
    ("p_liu_bang_qin", "p_zhang_liang", "served_under", None, None, 189, None, None),
    ("p_liu_bang_qin", "p_han_xin", "served_under", None, None, 196, None, "大将军"),
    ("p_liu_bang_qin", "p_caocan", "served_under", None, None, None, None, None),
    ("p_liu_bang_qin", "p_fan_kuai", "served_under", None, None, None, None, None),
    ("p_liu_bang_qin", "p_chen_ping", "served_under", None, None, None, None, None),
    ("p_han_xin", "e_gaixia_zhizhan", "led", 202, 12, None, None, "指挥"),
    ("p_lv_zhi", "p_liu_bang_qin", "spouse_of", None, None, 195, 6, None),
    ("p_lv_zhi", "p_han_xin", "killed", 196, None, None, None, "诛韩信"),
    ("p_xiao_he", "p_han_xin", "mentored_by", None, None, None, None, "萧何月下追韩信"),
    ("p_xiao_he", "p_lv_zhi", "allied_with", None, None, None, None, "诛韩信"),

    # 西汉
    ("p_liu_heng", "k_xihan", "succeeded_by", 180, None, 157, None, "文帝"),
    ("p_liu_qi", "k_xihan", "succeeded_by", 157, None, 141, None, "景帝"),
    ("p_liu_heng", "p_liu_qi", "father_of", 188, None, None, None, None),
    ("p_liu_qi", "p_liu_che", "father_of", 156, None, None, None, None),
    ("p_liu_che", "k_xihan", "succeeded_by", 141, None, 87, None, "武帝"),
    ("p_liu_che", "p_liu_fuling", "father_of", 94, None, None, None, None),
    ("p_liu_fuling", "k_xihan", "succeeded_by", 87, None, 74, None, "昭帝"),
    ("p_liu_xun", "k_xihan", "succeeded_by", 74, None, 49, None, "宣帝"),
    ("p_liu_ao", "k_xihan", "succeeded_by", 33, None, 7, None, "成帝"),
    ("p_zhao_feiyan", "p_liu_ao", "spouse_of", None, None, 7, None, None),
    ("p_liu_heng", "e_wen_jing_zhizhi", "participated_in", 180, None, 157, None, "主导"),
    ("p_liu_qi", "e_wen_jing_zhizhi", "participated_in", 157, None, 141, None, "主导"),
    ("p_liu_qi", "e_qiguo_zhiluan", "participated_in", 154, 1, 154, 3, "主导"),
    ("p_liu_che", "e_tui_en_ling", "participated_in", 127, None, None, None, "采纳主父偃策"),
    ("p_wei_qing", "p_liu_che", "served_under", None, None, 106, None, None),
    ("p_huo_qubing", "p_liu_che", "served_under", None, None, 117, None, None),
    ("p_wei_qing", "p_huo_qubing", "uncle_of", None, None, None, None, "舅侄"),
    ("p_wei_qing", "e_mobei_zhizhan", "led", 119, None, None, None, None),
    ("p_huo_qubing", "e_mobei_zhizhan", "led", 119, None, None, None, "封狼居胥"),
    ("p_zhang_qian", "p_liu_che", "served_under", None, None, 114, None, None),
    ("p_zhang_qian", "e_zhang_qian_xiyu", "participated_in", 138, None, 114, None, "凿空"),
    ("p_su_wu", "p_liu_che", "served_under", None, None, None, None, None),
    ("p_huo_guang", "p_liu_fuling", "served_under", 87, None, 68, None, "辅政"),
    ("p_huo_guang", "p_liu_xun", "served_under", 74, None, 66, None, "立宣帝"),
    ("p_dong_zhongshu", "p_liu_che", "served_under", None, None, None, None, "天人三策"),
    ("p_sima_qian", "p_liu_che", "served_under", None, None, 91, None, "太史令"),
    ("p_liu_che", "e_wugu_zhi_huo", "participated_in", 91, None, None, None, "晚年悲剧"),
    ("p_liu_che", "e_mobei_zhizhan", "participated_in", 119, None, None, None, "主导"),

    # 新
    ("p_wang_mang", "k_xin", "founded", 9, 1, None, None, "代汉建新"),
    ("p_wang_mang", "k_xihan", "usurped", 9, 1, None, None, None),
    ("p_wang_mang", "e_wang_mang_chuan_han", "participated_in", 9, 1, None, None, "主导"),
    ("p_wang_mang", "e_wang_mang_gaige", "participated_in", 9, None, 22, None, "主导"),

    # 东汉
    ("p_liu_xiu", "k_donghan", "founded", 25, None, None, None, "都洛阳"),
    ("p_liu_xiu", "k_xin", "usurped", 23, None, None, None, "灭新"),
    ("p_liu_xiu", "e_kunyang_zhizhan", "led", 23, 6, None, None, "8000破42万"),
    ("p_liu_xiu", "e_guangwu_zhongxing", "participated_in", 25, None, 57, 3, "主导"),
    ("p_liu_xiu", "e_lvlin_chimei", "participated_in", 22, None, 27, None, "更始帝后自立"),
    ("p_liu_zhuang_dong", "k_donghan", "succeeded_by", 57, None, 75, None, "明帝"),
    ("p_liu_da_dong", "k_donghan", "succeeded_by", 75, None, 88, None, "章帝"),
    ("p_liu_xiu", "p_liu_zhuang_dong", "father_of", 28, None, None, None, None),
    ("p_liu_zhuang_dong", "p_liu_da_dong", "father_of", 57, None, None, None, None),
    ("p_ban_chao", "p_liu_zhuang_dong", "served_under", 73, None, 88, None, None),
    ("p_ban_chao", "e_banchao_xiyu", "led", 73, None, 102, None, None),
    ("p_ban_chao", "p_ban_gu", "sibling_of", None, None, None, None, "兄弟"),
    ("p_dou_xian", "e_baihu_guan_huiyi", "participated_in", None, None, None, None, None) if False else None,
    ("p_dou_xian", "p_liu_zhuang_dong", "served_under", None, None, 92, None, "窦太后兄"),
    ("p_ma_yuan_dong", "p_liu_xiu", "served_under", None, None, 49, None, None),
    ("p_zhang_heng", "p_liu_da_dong", "served_under", None, None, None, None, None) if False else
    ("p_zhang_heng", "k_donghan", "served_under", 78, None, 139, None, None),
    ("p_cai_lun", "k_donghan", "served_under", 75, None, 121, None, "宦官"),

    # 黄巾
    ("p_zhang_jiao", "e_huangjin_qiyi", "participated_in", 184, 3, 184, 9, "领袖"),
    ("p_zhang_jiao", "p_zhang_bao", "sibling_of", None, None, None, None, "兄弟"),

    # 汉末群雄
    ("p_dong_zhuo", "e_dong_zhuo_luan_zheng", "participated_in", 189, 8, 192, 5, "主导"),
    ("p_dong_zhuo", "p_lv_bu", "served_under", None, None, 192, 5, "义父子"),
    ("p_lv_bu", "p_dong_zhuo", "killed", 192, 5, None, None, "与王允合谋"),
    ("p_yuan_shao", "e_dong_zhuo_luan_zheng", "participated_in", 190, None, None, None, "关东联军盟主"),
    ("p_yuan_shao", "e_guandu_zhizhan", "participated_in", 200, 2, None, None, "战败"),

    # 因果链
    ("e_qin_mie_liuguo", "e_fenshu_kengru", "preceded_by", None, None, None, None, "统一后强化思想控制"),
    ("e_fenshu_kengru", "e_daze_xiang_qiyi", "preceded_by", None, None, None, None, "暴政引发起义"),
    ("e_daze_xiang_qiyi", "e_julu_zhizhan", "preceded_by", None, None, None, None, "起义→秦亡"),
    ("e_julu_zhizhan", "e_chuhan_zhanzheng", "preceded_by", None, None, None, None, "秦亡后楚汉争霸"),
    ("e_chuhan_zhanzheng", "e_qiguo_zhiluan", "preceded_by", None, None, None, None, "汉朝建立后,巩固中央"),
    ("e_qiguo_zhiluan", "e_wen_jing_zhizhi", "preceded_by", None, None, None, None, "稳定后休养生息"),
    ("e_wen_jing_zhizhi", "e_mobei_zhizhan", "preceded_by", None, None, None, None, "国力强盛→主动出击"),
    ("e_wugu_zhi_huo", "e_wang_mang_chuan_han", "preceded_by", None, None, None, None, "西汉晚期乱局"),
    ("e_wang_mang_chuan_han", "e_kunyang_zhizhan", "preceded_by", None, None, None, None, "新朝暴政"),
    ("e_kunyang_zhizhan", "e_guangwu_zhongxing", "preceded_by", None, None, None, None, "新亡东汉立"),
    ("e_danggu_zhi_huo", "e_huangjin_qiyi", "preceded_by", None, None, None, None, "党锢→黄巾"),
    ("e_huangjin_qiyi", "e_dong_zhuo_luan_zheng", "preceded_by", None, None, None, None, "黄巾→军阀混战"),
    ("e_dong_zhuo_luan_zheng", "e_guandu_zhizhan", "preceded_by", None, None, None, None, "军阀混战→官渡"),
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
    out = DATA / "relations" / "qin_han.yaml"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(deduped, f, allow_unicode=True, sort_keys=False)
    print(f"  ✓ {len(deduped)} relations → data/relations/qin_han.yaml")


if __name__ == "__main__":
    print(f"→ Phase 12: Qin + Han (BC 221-220)")
    gen_places()
    print(f"  ✓ {len(PLACES)} places")
    gen_birthplaces()
    print(f"  ✓ {len(EXTRA_BIRTH)} birthplaces")
    gen_polities()
    print(f"  ✓ {len(POLITIES)} polities")
    gen_persons()
    print(f"  ✓ {len(PERSONS)} persons")
    gen_events()
    print(f"  ✓ {len(EVENTS)} events")
    gen_relations()
    print("Done.")
