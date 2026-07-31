#!/usr/bin/env python3
"""Phase 14 — Yuan / Ming / Qing (1206-1912).

Final batch covering Mongol/Yuan, Ming, Qing. Many key Mongol figures
(成吉思汗/窝阔台/拖雷/蒙哥/忽必烈/耶律楚材) already created in seed_song.py.
This batch adds Ming + Qing emperors, key ministers, late imperial factions,
major events (元末红巾、靖难、土木堡、张居正改革、康乾盛世、鸦片战争、
太平天国、甲午、戊戌、辛亥), and the transition figures (朱元璋/多尔衮/郑成功/吴三桂).
"""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)


PERSONS = [
    # ===== 明朝皇帝(朱元璋、忽必烈已存在) =====
    ("p_jianwen", "朱允炆", ["建文帝", "明惠宗"], None, (1377, None), (1402, None), "pl_nanjing_ming2",
     "明第二任皇帝。太祖孙,懿文太子朱标子。1398 即位。削藩引发靖难。1402 南京城破,下落成谜。", ["明史·恭闵帝本纪"]),
    ("p_yongle", "朱棣", ["明成祖", "明太宗"], None, (1360, None), (1424, 7), "pl_beiping_zhudi",
     "明成祖,太祖第四子,燕王。1399-1402 靖难之役夺位。1421 迁都北京。1405-1433 命郑和下西洋。五征漠北。编纂《永乐大典》。", ["明史·成祖本纪"]),
    ("p_hongxi", "朱高炽", ["明仁宗"], None, (1378, None), (1425, None), "pl_beiping_zhudi",
     "明仁宗。永乐帝长子。1424 即位,在位十月。", ["明史·仁宗本纪"]),
    ("p_xuande", "朱瞻基", ["明宣宗"], None, (1399, None), (1435, None), "pl_beiping_zhudi",
     "明宣宗。仁宗子。仁宣之治。1426 平汉王叛,1430 命郑和末航。", ["明史·宣宗本纪"]),
    ("p_zhengtong", "朱祁镇", ["明英宗"], None, (1427, None), (1464, None), "pl_beiping_zhudi",
     "明英宗。宣宗子。1435-1449 第一次在位。1449 土木堡之变被瓦剌俘。1457 夺门之变复辟,1457-1464 第二次在位。", ["明史·英宗本纪"]),
    ("p_jingtai", "朱祁钰", ["明代宗", "景泰帝"], None, (1428, None), (1457, None), "pl_beiping_zhudi",
     "明代宗。宣宗次子,英宗弟。1449 英宗被俘后即位。1449 北京保卫战(于谦)。1457 夺门之变英宗复辟,被废郕王。", ["明史·景帝纪"]),
    ("p_chenghua", "朱见深", ["明宪宗"], None, (1447, None), (1487, None), "pl_beiping_zhudi",
     "明宪宗。英宗子。成化新风。设西厂。", ["明史·宪宗本纪"]),
    ("p_hongzhi", "朱祐樘", ["明孝宗"], None, (1470, None), (1505, None), "pl_beiping_zhudi",
     "明孝宗。弘治中兴。明代少有的贤君。", ["明史·孝宗本纪"]),
    ("p_zhengde", "朱厚照", ["明武宗"], None, (1491, None), (1521, None), "pl_beiping_zhudi",
     "明武宗。建豹房。1519 宁王之乱(王守仁平)。", ["明史·武宗本纪"]),
    ("p_jiajing", "朱厚熜", ["明世宗", "嘉靖"], None, (1507, None), (1567, 1), "pl_beiping_zhudi",
     "明世宗。宪宗孙,兴献王子,正德堂弟。1521 入继大统。1521 大礼议。1550 庚戌之变(俺答犯京)。后期沉迷修道。", ["明史·世宗本纪"]),
    ("p_longqing", "朱载坖", ["明穆宗", "隆庆"], None, (1537, None), (1572, None), "pl_beiping_zhudi",
     "明穆宗。世宗子。1567 隆庆开关。1571 俺答封贡。", ["明史·穆宗本纪"]),
    ("p_wanli", "朱翊钧", ["明神宗", "万历"], None, (1563, None), (1620, 8), "pl_beiping_zhudi",
     "明神宗。穆宗子。1572 10 岁即位。1573-1582 张居正改革。1592-1598 万历朝鲜之役(抗倭援朝)。1619 萨尔浒败于后金。在位 48 年(明最长)。", ["明史·神宗本纪"]),
    ("p_taichang", "朱常洛", ["明光宗", "泰昌"], None, (1582, None), (1620, 9), "pl_beiping_zhudi",
     "明光宗。神宗长子。1620 八月即位,在位一月。红丸案。", ["明史·光宗本纪"]),
    ("p_tianqi", "朱由校", ["明熹宗", "天启"], None, (1605, None), (1627, None), "pl_beiping_zhudi",
     "明熹宗。光宗子。魏忠贤专权,朝政日乱。", ["明史·熹宗本纪"]),
    ("p_chongzhen", "朱由检", ["明思宗", "崇祯"], None, (1611, None), (1644, 3), "pl_beiping_zhudi",
     "明思宗。光宗第五子,熹宗弟。1627 即位,即除魏忠贤。但刚愎自用,屡易大臣。明末农民起义。1644 三月李自成入京,煤山自缢,明亡。", ["明史·庄烈帝本纪"]),

    # ===== 南明 =====
    ("p_hongguang", "朱由崧", ["弘光帝"], None, (1607, None), (1646, None), "pl_nanjing_ming2",
     "南明第一位皇帝。福王朱由崧。1644-1645 在位。1645 南京陷被俘。", ["明史·福王传"]),
    ("p_longwu", "朱聿键", ["隆武帝"], None, (1602, None), (1646, None), "pl_fuzhou_longwu",
     "南明第二位。唐王朱聿键。1645-1646 在位。", ["明史·唐王传"]),
    ("p_yongli", "朱由榔", ["永历帝"], None, (1623, None), (1662, None), "pl_zhaoqing_yongli",
     "南明末帝。桂王朱由榔。1646-1662 在位。流亡缅甸。1662 缅甸交吴三桂,绞死于昆明。南明亡。", ["明史·桂王传"]),

    # ===== 明开国功臣 =====
    ("p_xuda", "徐达", ["徐天德"], "天德", (1332, None), (1385, None), "pl_haozhou_xu",
     "明开国第一功臣,右丞相、魏国公。1367 平张士诚。1368 北伐克大都。", ["明史·徐达传"]),
    ("p_changyuchun", "常遇春", ["常伯仁"], "伯仁", (1330, None), (1369, None), "pl_haozhou_chang",
     "明开国骁将,鄂国公。1369 北伐卒于军。", ["明史·常遇春传"]),
    ("p_liuji", "刘基", ["刘伯温", "诚意伯"], None, (1311, None), (1375, None), "pl_qingtian_liu",
     "明开国谋臣。'三分天下诸葛亮,一统江山刘伯温'。", ["明史·刘基传"]),
    ("p_lishanchang", "李善长", ["韩国公"], None, (1314, None), (1390, None), "pl_dingyuan_li",
     "明开国首辅,左丞相。1390 胡惟庸案株连处死。", ["明史·李善长传"]),
    ("p_lanyu", "蓝玉", ["凉国公"], None, (None, None), (1393, None), "pl_dingyuan_lan",
     "明开国骁将。1388 捕鱼儿海破北元。1393 蓝玉案被诛。", ["明史·蓝玉传"]),

    # ===== 靖难 / 明中名臣 =====
    ("p_yaoguangxiao", "姚广孝", ["道衍"], None, (1335, None), (1418, None), "pl_changzhou_yao",
     "靖难主谋,僧人、太子少师。", ["明史·姚广孝传"]),
    ("p_yuqian", "于谦", ["于廷益"], "廷益", (1398, None), (1457, None), "pl_qiantang_yu",
     "明名将、兵部尚书。1449 北京保卫战大败瓦剌。1457 夺门之变后被杀。", ["明史·于谦传"]),
    ("p_wangshouren", "王守仁", ["王阳明"], "伯安", (1472, None), (1529, None), "pl_yuyao_wang",
     "明代思想家、军事家。心学集大成者。1508 龙场悟道。1519 平宁王之乱。", ["明史·王守仁传"]),
    ("p_zhangjuzheng", "张居正", ["张叔大", "张太岳"], "叔大", (1525, None), (1582, None), "pl_jiangling_zhang",
     "明代政治家、改革家。万历初年内阁首辅。1573 考成法。1581 一条鞭法。死后被清算。", ["明史·张居正传"]),
    ("p_hairui", "海瑞", ["海刚峰"], "汝贤", (1514, None), (1587, None), "pl_qiongshan_hai",
     "明代清官。1566 上《治安疏》骂嘉靖,几乎处死。", ["明史·海瑞传"]),
    ("p_qijiguang", "戚继光", ["戚元敬"], "元敬", (1528, None), (1588, None), "pl_dengzhou_qi",
     "明代抗倭名将。1561 台州大捷。后镇蓟门。", ["明史·戚继光传"]),
    ("p_yansong", "严嵩", ["严惟中"], "惟中", (1480, None), (1567, None), "pl_fenyi_yan",
     "明代权奸,首辅。专国二十年。1562 倒台。", ["明史·奸臣传·严嵩"]),
    ("p_weizhongxian", "魏忠贤", ["魏太监", "九千岁"], None, (1568, None), (1627, None), "pl_hejian_wei",
     "明代宦官,司礼监秉笔太监。天启朝阉党首领,称'九千岁'。1627 崇祯即位自缢。", ["明史·宦官传·魏忠贤"]),

    # ===== 明末农民起义 + 明清易代 =====
    ("p_lizicheng", "李自成", ["李闯", "闯王"], None, (1606, None), (1645, None), "pl_mizhi_li",
     "明末农民起义领袖。1644.3 入北京,明亡。山海关败于清军。1645 湖北九宫山死(存疑)。", ["明史·流贼传"]),
    ("p_zhangxianzhong", "张献忠", None, None, (1606, None), (1647, None), "pl_dingbian_zhang",
     "明末农民起义领袖。1644 入川称帝(大西)。1647 西充中箭死。", ["明史·流贼传"]),
    ("p_duoergun", "多尔衮", ["睿亲王"], None, (1612, None), (1650, None), "pl_hetuala_dor",
     "清摄政王。1644 入关定鼎。剃发易服。", ["清史稿·多尔衮传"]),
    ("p_wusan_gui", "吴三桂", ["平西王"], None, (1612, None), (1678, None), "pl_gaoyou_wu",
     "明山海关总兵。1644 引清军入关。后封平西王。1673-1678 三藩之乱,称帝,死。", ["清史稿·吴三桂传"]),
    ("p_shikefa", "史可法", None, None, (1601, None), (1645, None), "pl_xiangfu_shi",
     "南明兵部尚书、东阁大学士。1645 扬州十日殉城。", ["明史·史可法传"]),
    ("p_zhengchenggong", "郑成功", ["国姓爷"], None, (1624, None), (1662, None), "pl_nan_an_zheng",
     "南明延平郡王。1661-1662 收复台湾。", ["清史稿·郑成功传"]),

    # ===== 后金/清初 =====
    ("p_nuerhaci", "努尔哈赤", ["清太祖"], None, (1559, None), (1626, None), "pl_hetuala_dor",
     "后金建立者。1583 起兵。1616 建后金。1619 萨尔浒之战。1626 宁远败于袁崇焕受创死。", ["清史稿·太祖本纪"]),
    ("p_huangtaiji", "皇太极", ["清太宗"], None, (1592, None), (1643, None), "pl_hetuala_dor",
     "清第二任。1635 改族名'满洲'。1636 改国号'大清'。1642 松锦之战灭洪承畴。", ["清史稿·太宗本纪"]),

    # ===== 清朝皇帝 =====
    ("p_shunzhi", "福临", ["清世祖", "顺治"], None, (1638, None), (1661, None), "pl_shenyang_qing",
     "清世祖。6 岁即位,多尔衮摄政。1644 入关定鼎。传说出家,实出痘死。", ["清史稿·世祖本纪"]),
    ("p_kangxi", "玄烨", ["清圣祖", "康熙"], None, (1654, None), (1722, None), "pl_beijing_qing",
     "清圣祖。中国历史上在位最久的皇帝(61 年)。1669 擒鳌拜。1681 平三藩。1683 收台湾(施琅)。1689 尼布楚条约。1690-1697 三征噶尔丹。", ["清史稿·圣祖本纪"]),
    ("p_yongzheng", "胤禛", ["清世宗", "雍正"], None, (1678, None), (1735, None), "pl_beijing_qing",
     "清世宗。摊丁入亩、火耗归公、改土归流。1729 设军机处。即位合法性争议(学界主流认为合法)。", ["清史稿·世宗本纪"]),
    ("p_qianlong", "弘历", ["清高宗", "乾隆"], None, (1711, None), (1799, None), "pl_beijing_qing",
     "清高宗。十全武功(1755-1792 两平准噶尔、平回部、大小金川等)。1773 开四库全书馆。1793 马戛尔尼使团。六下江南。", ["清史稿·高宗本纪"]),
    ("p_jiaqing", "颙琰", ["清仁宗", "嘉庆"], None, (1760, None), (1820, None), "pl_beijing_qing",
     "清仁宗。1799 诛和珅('和珅跌倒,嘉庆吃饱')。1813 天理教林清之变。", ["清史稿·仁宗本纪"]),
    ("p_daoguang", "旻宁", ["清宣宗", "道光"], None, (1782, None), (1850, None), "pl_beijing_qing",
     "清宣宗。1839 林则徐虎门销烟。1840-1842 鸦片战争。1842 南京条约(割香港、开五口)。", ["清史稿·宣宗本纪"]),
    ("p_xianfeng", "奕詝", ["清文宗", "咸丰"], None, (1831, None), (1861, None), "pl_beijing_qing",
     "清文宗。1851 太平天国起。1856-1860 第二次鸦片战争。1860 逃热河,圆明园被焚。", ["清史稿·文宗本纪"]),
    ("p_tongzhi", "载淳", ["清穆宗", "同治"], None, (1856, None), (1875, None), "pl_beijing_qing",
     "清穆宗。两宫太后(慈安、慈禧)垂帘。1861-1895 同治中兴(洋务运动)。", ["清史稿·穆宗本纪"]),
    ("p_guangxu", "载湉", ["清德宗", "光绪"], None, (1871, None), (1908, None), "pl_beijing_qing",
     "清德宗。1894-1895 甲午战争。1898 戊戌变法(百日维新)。1900 庚子拳乱,西狩西安。1908.11.14 暴卒(检鉴定砷中毒)。", ["清史稿·德宗本纪"]),
    ("p_xuantong", "溥仪", ["宣统", "逊帝"], None, (1906, None), (1967, None), "pl_beijing_qing",
     "清末代皇帝。1908-1912 在位。1912.2.12 退位,帝制终结。1917 张勋复辟(12日)。1932-1945 伪满洲国。", ["清史稿·宣统本纪"]),

    # ===== 清代名臣 =====
    ("p_heshen", "和珅", ["致斋"], None, (1750, None), (1799, None), "pl_beijing_qing_heshen",
     "清代权臣。大学士、军机大臣。1799 嘉庆赐自尽。抄家产值传说八亿两。", ["清史稿·和珅传"]),
    ("p_linzexu", "林则徐", ["林元抚"], "元抚", (1785, None), (1850, None), "pl_houguan_lin",
     "清代政治家、民族英雄。1839 钦差大臣,虎门销烟。鸦片战争后被贬。", ["清史稿·林则徐传"]),
    ("p_zengguofan", "曾国藩", ["曾伯涵", "曾文正"], "伯涵", (1811, None), (1872, None), "pl_xiangxiang_zeng",
     "晚清政治家、军事家。1853 创湘军。1864 克南京灭太平天国。", ["清史稿·曾国藩传"]),
    ("p_zuozongtang", "左宗棠", ["左季高"], "季高", (1812, None), (1885, None), "pl_xiangyin_zuo",
     "晚清名将。1876-1878 收复新疆。", ["清史稿·左宗棠传"]),
    ("p_lihongzhang", "李鸿章", ["李少荃"], "少荃", (1823, None), (1901, None), "pl_hefei_li",
     "晚清政治家、洋务派领袖。1862 创淮军。办洋务。1895 马关签约。1901 辛丑签约。", ["清史稿·李鸿章传"]),
    ("p_zhangzhidong", "张之洞", ["张孝达", "张香涛"], "孝达", (1837, None), (1909, None), "pl_nanpi_zhang",
     "晚清洋务后期领袖。1889 始建汉阳铁厂。1898《劝学篇》'中体西用'。", ["清史稿·张之洞传"]),
    ("p_yuanshikai", "袁世凯", ["慰亭"], "慰亭", (1859, None), (1916, None), "pl_xiangcheng_yuan",
     "晚清民初政治军事家。1895 小站练兵。1912 窃任大总统。1915 称帝(失败)。", ["清史稿·袁世凯传"]),

    # ===== 后妃 =====
    ("p_cixi", "慈禧太后", ["叶赫那拉·杏贞", "西太后"], None, (1835, None), (1908, None), "pl_beijing_qing_cixi",
     "晚清实际最高统治者,同治、光绪两朝垂帘听政 47 年。1861 辛酉政变。1898 戊戌政变。1900 庚子西狩。", ["清史稿·后妃传"]),
    ("p_cian", "慈安太后", ["钮祜禄氏", "东太后"], None, (1837, None), (1881, None), "pl_beijing_qing",
     "咸丰皇后,东太后。1881 暴卒(疑被慈禧害,学界存疑)。", ["清史稿·后妃传"]),

    # ===== 太平天国 =====
    ("p_hongxiuquan", "洪秀全", ["天王"], None, (1814, None), (1864, None), "pl_huaxian_hong",
     "太平天国领袖。1837 异梦,1843 创拜上帝会。1851 金田起义,建号太平天国,称天王。1864 天京陷落前病死。", ["清史稿·洪秀全传"]),
    ("p_yangxiuqing", "杨秀清", ["东王"], None, (None, None), (1856, None), "pl_guiping_yang",
     "太平天国东王。'天父下凡'。1856 天京事变被杀。", ["清史稿·洪秀全传附"]),
    ("p_shidakai", "石达开", ["翼王"], None, (1831, None), (1863, None), "pl_guiping_shi",
     "太平天国翼王。天京事变后出走。1863 大渡河败亡。", ["清史稿·洪秀全传附"]),

    # ===== 元末群雄(除朱元璋)=====
    ("p_hanshantong", "韩山童", None, None, (None, None), (1351, None), "pl_luan_han",
     "元末红巾军首领。自称宋徽宗八世孙。1351 起义即事泄被杀。", ["明史·韩林儿传"]),
    ("p_liufutong", "刘福通", None, None, (None, None), (1363, None), "pl_yingzhou_liu",
     "元末红巾军首领。1351 颍州起义。1355 拥立韩林儿为小明王建宋。", ["明史·韩林儿传"]),
    ("p_chenyouliang", "陈友谅", None, None, (1320, None), (1363, None), "pl_qishui_chen",
     "元末群雄。1360 杀徐寿辉称帝(汉)。1363 鄱阳湖之战中箭死。", ["明史·陈友谅传"]),
    ("p_zhangshicheng", "张士诚", None, None, (1321, None), (1367, None), "pl_dongtai_zhang",
     "元末群雄。私盐贩出身。降元。后为朱元璋所灭。", ["明史·张士诚传"]),

    # ===== 元朝皇帝(补充) =====
    ("p_tiemur", "铁穆耳", ["元成宗"], None, (1265, None), (1307, None), "pl_dadu_yuan",
     "元成宗,忽必烈孙。守成之君,元中期相对稳定。", ["元史·成宗本纪"]),
    ("p_a_yu", "爱育黎拔力八达", ["元仁宗"], None, (1285, None), (1320, None), "pl_dadu_yuan",
     "元仁宗。1313 诏行科举(延祐复科)。", ["元史·仁宗本纪"]),
    ("p_tuogantimur", "妥懽帖睦尔", ["元惠宗", "元顺帝"], None, (1320, None), (1370, None), "pl_dadu_yuan",
     "元末代皇帝(在中原)。1333-1368 在位。1351 红巾起义。1368 退出大都,北走应昌,北元始。明太祖上尊号'顺帝'。", ["元史·顺帝本纪"]),
    ("p_tuotuo_yuan", "脱脱", ["脱脱大用"], "大用", (1314, None), (1356, None), "pl_dadu_yuan_tuotuo",
     "元末权臣。1340 至正更化,主政改革。1344 主修辽金宋三史。后贬死。", ["元史·脱脱传"]),
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
        if pid in ("p_cixi", "p_cian"):
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
    ("k_minguo", "中华民国", "Republic of China", "#3498db", (1912, 1), (1949, 9), "p_sunzhongshan", "pl_nanjing_minguo", "d_qing", None,
     "1912 年 1 月 1 日孙中山就任临时大总统,中华民国建立。1949 年国民政府迁台。", "孙中山全集;中华民国史"),
]
def gen_polities():
    for tup in POLITIES:
        pid, name, en, color, founded, ended, founder, capital, supplanted, ended_by, desc, src = tup
        obj = {
            "id": pid, "type": "Polity", "name": name, "name_en": en, "color": color,
            "founded": {"year": founded[0], "month": founded[1]} if founded[1] else {"year": founded[0]},
            "ended": {"year": ended[0], "month": ended[1]} if ended[1] else {"year": ended[0]},
            "capital": capital, "description": desc, "sources": src.split(";") if isinstance(src, str) else src,
        }
        if founder: obj["founder"] = founder
        if supplanted: obj["supplanted"] = supplanted
        if ended_by: obj["ended_by"] = ended_by
        write(DATA / "entities" / "polities" / f"{pid[2:]}.yaml", obj)


# 派系
FACTIONS = [
    ("f_huaixi_ji", "明淮西将帅集团", "military_clan", (1352, None), (1393, None), "pl_haozhou_xu",
     "朱元璋起家于濠州(凤阳),淮西将帅为开国核心:李善长、徐达、常遇春、汤和、邓愈、蓝玉等。1380 胡惟庸案、1393 蓝玉案双案清洗。",
     "明初开国军功集团。", ["李善长", "徐达", "常遇春", "汤和", "蓝玉"], "1352-1393"),
    ("f_jingnan_ji", "靖难功臣集团", "military_clan", (1399, None), (1424, None), "pl_beiping_zhudi",
     "朱棣燕藩嫡系。姚广孝为谋主,张玉、朱能、丘福等为将。靖难之役夺位。1410 丘福北征全军覆没。",
     "明成祖朝统治核心。", ["朱棣", "姚广孝", "张玉", "朱能"], "1399-1424"),
    ("f_donglin_dang", "东林党", "political", (1604, None), (1627, None), "pl_wuxi_donglin",
     "万历三十年(1604)顾宪成重修无锡东林书院,讲学议政。天启朝与阉党对抗。'东林七贤'前六君子(杨涟、左光斗等)被魏忠贤杀害。1627 崇祯除魏忠贤,平反东林。",
     "明末影响最大的士大夫政治集团。", ["顾宪成", "杨涟", "左光斗", "高攀龙"], "1604-1627"),
    ("f_yandang", "阉党", "political", (1620, None), (1627, None), "pl_beijing_qing",
     "魏忠贤为首的宦官集团,称'九千岁'。1625-1627 大兴党狱。1627 崇祯除魏忠贤。",
     "明末宦官专权顶峰。", ["魏忠贤", "崔呈秀"], "1620-1627"),
    ("f_xiangjun", "湘军系", "military_clan", (1853, None), (1949, None), "pl_xiangxiang_zeng",
     "曾国藩 1853 创湘军平太平天国。湖南籍军人官僚集团。左宗棠、彭玉麟、胡林翼、曾国荃。",
     "晚清军政主要势力,'同治中兴'主导。", ["曾国藩", "左宗棠", "胡林翼", "彭玉麟"], "1853-"),
    ("f_huaijun_bei_yang", "淮军 → 北洋系", "military_clan", (1862, None), (1928, None), "pl_hefei_li",
     "李鸿章 1862 创淮军。后演化出北洋系:1895 袁世凯小站练兵新建陆军。段祺瑞、冯国璋、王士珍、曹锟。",
     "晚清至民国初年的实际军政主宰。", ["李鸿章", "袁世凯", "段祺瑞", "冯国璋"], "1862-1928"),
    ("f_taiping", "太平天国", "military_clan", (1851, None), (1864, None), "pl_tianjing_taiping",
     "1851 金田起义,建号太平天国。洪秀全为天王,杨秀清(东王)、萧朝贵(西王)、冯云山(南王)、韦昌辉(北王)、石达开(翼王)并立。1856 天京事变内讧。1864 湘军破南京。",
     "中国历史上规模最大的农民战争。", ["洪秀全", "杨秀清", "石达开", "韦昌辉"], "1851-1864"),
    ("f_tongmenghui", "同盟会(革命党)", "political", (1905, None), (1912, None), "pl_dongjing_tongmeng",
     "1905 孙中山、黄兴、宋教仁等在东京成立中国同盟会。'驱除鞑虏,恢复中华,创立民国,平均地权'。",
     "辛亥革命的主导力量。", ["孙中山", "黄兴", "宋教仁", "章炳麟"], "1905-1912"),
]
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
        obj["sources"] = ["明史", "清史稿"]
        write(DATA / "entities" / "factions" / f"{fid[2:]}.yaml", obj)


# 战役
BATTLES = [
    ("b_poyanghu", "鄱阳湖之战", (1363, 8), None, "pl_poyanghu",
     ["k_yuan_pre", "k_wu_zhang", "k_han_chen"], ["p_zhuyuanzhang", "p_chenyouliang"], "k_wu_zhang", "p_zhuyuanzhang",
     "朱元璋与陈友谅的决战。陈友谅率六十万(号)水师,巨舰连锁。朱元璋以小船火攻,陈中箭死。",
     "朱元璋统一江南的决定性战役。", "明史·太祖本纪"),
    ("e_tumubao", "土木堡之变", (1449, 9), None, "pl_tumubao",
     ["k_ming", "k_waci"], ["p_zhengtong", "p_xianxian_waci"], "k_waci", "p_xianxian_waci",
     "1449 瓦剌也先犯边。太监王振怂英宗亲征。退兵时绕道,致在土木堡被围。明军 50 万(号)崩溃,英宗被俘,王振死。",
     "明初以来最大军事灾难,精锐尽失。", "明史·英宗本纪"),
    ("e_beijing_bao_wei", "北京保卫战", (1449, 10), None, "pl_beijing_qing",
     ["k_ming", "k_waci"], ["p_yuqian"], "k_ming", "p_yuqian",
     "土木堡后于谦力主抗战,拥立景泰帝,固守北京。瓦剌攻城不克,退。",
     "保住明朝。", "明史·于谦传"),
    ("b_sarhu", "萨尔浒之战", (1619, 4), None, "pl_sarhu",
     ["k_ming", "k_houjin"], ["p_yanghao_ming", "p_nuerhaci"], "k_houjin", "p_nuerhaci",
     "明四路围剿后金。杨镐指挥。努尔哈赤'凭尔几路来,我只一路去',集中兵力各个击破。明军大败。",
     "辽东易势,后金崛起不可挡。", "清史稿·太祖本纪"),
    ("b_ningyuan", "宁远之战", (1626, None), None, "pl_ningyuan",
     ["k_ming", "k_houjin"], ["p_yuanchonghuan", "p_nuerhaci"], "k_ming", "p_yuanchonghuan",
     "努尔哈赤攻宁远。袁崇焕用红夷大炮坚守。努尔哈赤受创(后病死)。", "明首次正面击败后金。", "明史·袁崇焕传"),
    ("b_shanhai_guan", "山海关之战", (1644, 5), None, "pl_shanhaiguan",
     ["k_qing", "k_dashun_li", "k_ming"], ["p_duoergun", "p_wusan_gui", "p_lizicheng"], "k_qing", "p_duoergun",
     "1644.5 吴三桂引清军入关。多尔衮率清军与吴三桂合击李自成于一片石。李败。清入北京。",
     "清朝定鼎中原之始。", "清史稿·世祖本纪"),
    ("b_yakin", "甲午海战(黄海)", (1894, 9), None, "pl_huang_hai",
     ["k_qing", "k_rib"], ["p_dingruchang", "p_itou_rit"], "k_rib", None,
     "1894.9 北洋水师提督丁汝昌率舰队在黄海大东沟遇日本联合舰队。激战 5 小时,北洋损失致远、经远等。李鸿章'保船制敌'。", "甲午战争转折。", "清史稿·海军志"),
]
def gen_battles():
    for tup in BATTLES:
        bid, name, date, end, place, combatants, commanders, victor, victor_cmd, desc, *rest = tup
        if len(rest) == 2:
            sig, srcs = rest
        else:
            sig = rest[0] if rest else ""
            srcs = ""
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
    ("e_hongjinjun_qiyi", "红巾军起义", (1351, 5), (1368, None), "institution", "pl_yingzhou_liu", ["k_yuan_pre"],
     "1351 五月刘福通、韩山童颍州起义。红巾为号。拥立韩林儿为小明王建宋。各路红巾军遍布全国。",
     "元朝崩溃直接原因。朱元璋原系红巾郭子兴部。", "明史·韩林儿传"),
    ("e_jingnan_zhiyi", "靖难之役", (1399, 7), (1402, 7), "coup", "pl_beijing_qing", ["k_ming"],
     "1399 七月燕王朱棣以'清君侧'为名起兵。1402 攻入南京,建文帝下落成谜,朱棣即位。",
     "明成祖夺位,迁都北京。", "明史·成祖本纪"),
    ("e_zhenghe_xiaxiyang", "郑和下西洋", (1405, None), (1433, None), "diplomacy", "pl_liujiagang", ["k_ming"],
     "1405-1433 郑和七下西洋(或言八)。船队庞大(200 余艘,2.7 万人)。最远抵东非、阿拉伯。",
     "世界航海史壮举。明朝官方主导,无经济目的,后因财政停罢。", "明史·郑和传"),
    ("e_tumubian", "土木堡之变", (1449, 9), None, "coup", "pl_tumubao", ["k_ming"],
     "1449 瓦剌也先犯边。太监王振怂英宗亲征。退兵绕道在土木堡被围,明军大溃,英宗被俘。",
     "明初军事灾难,精锐尽失。于谦北京保卫战保住明朝。", "明史·英宗本纪"),
    ("e_duomen_zhibian", "夺门之变", (1457, None), None, "coup", "pl_beijing_qing", ["k_ming"],
     "1457 石亨、徐有贞趁景泰帝病重,拥英宗复辟。于谦被杀。",
     "明朝政争。", "明史·英宗本纪"),
    ("e_daliyi", "大礼议", (1521, None), (1524, None), "institution", "pl_beijing_qing", ["k_ming"],
     "1521 武宗崩无子,堂弟朱厚熜(世宗)入继。世宗欲尊生父为帝,与朝臣(杨廷和等)对立。1524 廷杖百余人,世宗胜。",
     "明世宗朝政治主线,加剧君臣对立。", "明史·世宗本纪"),
    ("e_gengxu_zhibian", "庚戌之变", (1550, None), None, "institution", "pl_beijing_qing", ["k_ming"],
     "1550 俺答汗犯京师。明廷许贡。", "明蒙关系事件。", "明史·世宗本纪"),
    ("e_wang_an_shi_zhang_juzheng", "张居正改革", (1573, None), (1582, None), "reform", "pl_beijing_qing", ["k_ming"],
     "1573 考成法(整顿吏治)。1577-1581 测全国土地(《鱼鳞图册》)。1581 一条鞭法(赋役合一,折银)。", "明朝后期最有力的改革,财政、军备、吏治一度好转。", "明史·张居正传"),
    ("e_kangxi_ping_sanfan", "平定三藩", (1673, 12), (1681, 10), "institution", "pl_kunming_wu", ["k_qing"],
     "1673 康熙撤藩。吴三桂(平西王,云南)、尚可喜(平南王,广东)、耿精忠(靖南王,福建)叛。1681 平定。",
     "清朝统一中国的关键。", "清史稿·圣祖本纪"),
    ("e_shou_taiwan", "收复台湾", (1683, None), None, "institution", "pl_taiwan_qing", ["k_qing"],
     "1683 施琅率福建水师克澎湖,郑克塽降。清朝收台湾,设台湾府。",
     "清朝版图扩展。", "清史稿·圣祖本纪"),
    ("e_yongzheng_gaige", "雍正改革", (1723, None), (1735, None), "reform", "pl_beijing_qing", ["k_qing"],
     "摊丁入亩(丁银并入田赋)。火耗归公(规范地方加派)。改土归流(西南少数民族地区由土司改流官)。1729 设军机处强化皇权。", "清朝集权与财政改革。", "清史稿·世宗本纪"),
    ("e_shiquan_wugong", "十全武功", (1755, None), (1792, None), "institution", "pl_beijing_qing", ["k_qing"],
     "乾隆自诩十大武功:两平准噶尔、平回部、大小金川、台湾林爽文、缅甸、安南、廓尔喀二。",
     "清鼎盛疆域形成(蒙古、新疆、西藏、台湾)。", "清史稿·高宗本纪"),
    ("e_ya_pian_zhanzheng", "第一次鸦片战争", (1840, 6), (1842, 8), "institution", "pl_guangzhou_ya", ["k_qing", "k_ying"],
     "1839.6 林则徐虎门销烟。1840.6 英军犯广东北犯。1842.8 南京条约:割香港、开五口(广厦福宁上)、赔款 2100 万银元。",
     "中国近代史开端,百年屈辱史起。", "清史稿·宣宗本纪"),
    ("e_taiping_tian_guo", "太平天国运动", (1851, 1), (1864, 6), "institution", "pl_jintian_taiping", ["k_qing", "k_taiping"],
     "1851.1 洪秀全金田起义,建太平天国。1853 占南京为天京。北伐、西征。1864 湘军曾国荃破南京。", "中国历史上规模最大的农民战争。", "清史稿·洪秀全传"),
    ("e_yang_wu_yun_dong", "洋务运动", (1861, None), (1895, None), "reform", "pl_beijing_qing", ["k_qing"],
     "自强求富。曾国藩、李鸿章、左宗棠、张之洞等兴办军工、洋务企业。'中体西用'。",
     "晚清现代化初步尝试。甲午一役宣告失败。", "清史稿"),
    ("e_jia_wu_zhanzheng", "甲午中日战争", (1894, 7), (1895, 4), "institution", "pl_korea_jia_wu", ["k_qing", "k_rib"],
     "1894.7 朝鲜东学党起义引发中日出兵。9 黄海海战。1895.2 威海卫陷,北洋水师覆没。1895.4 马关条约(割台澎辽、赔 2 亿两)。",
     "洋务运动破产。中国民族危机加深,刺激维新。", "清史稿·德宗本纪"),
    ("e_wu_xu_bian_fa", "戊戌变法", (1898, 6), (1898, 9), "reform", "pl_beijing_qing", ["k_qing"],
     "1898.6.11 明定国是诏始。康有为、梁启超、谭嗣同等推动新政。9.21 慈禧政变,光绪囚,六君子(谭嗣同等)杀,变法止。",
     "近代政治改革尝试。", "清史稿·德宗本纪"),
    ("e_gengzi_qiyi", "义和团运动", (1900, None), (1901, 9), "institution", "pl_beijing_qing", ["k_qing"],
     "1900 民间反洋教运动。慈禧利用宣战。八国联军攻陷北京,慈禧西狩。1901 辛丑条约赔 4.5 亿两。",
     "晚清民族主义运动。", "清史稿·德宗本纪"),
    ("e_xin_hai_ge_ming", "辛亥革命", (1911, 10), (1912, 2), "coup", "pl_wuchang_xinhai", ["k_qing", "k_minguo"],
     "1911.10.10 武昌起义,各省响应。1912.1.1 孙中山就任临时大总统,中华民国建立。1912.2.12 隆裕太后颁《退位诏书》,清亡,帝制终结。",
     "结束两千多年帝制,中国进入共和时代。", "清史稿·宣统本纪;中华民国史"),
]
def gen_events():
    for tup in EVENTS:
        eid, name, date, end, category, place, polities, desc, impact, srcs = tup
        obj = {
            "id": eid, "type": "Event", "name": name,
            "date": {"year": date[0]} if not date[1] else {"year": date[0], "month": date[1]},
            "category": category, "location": place,
            "polities_involved": polities,
            "description": desc, "impact": impact,
            "sources": srcs.split(";") if isinstance(srcs, str) else srcs,
        }
        if end and end[0]:
            obj["end_date"] = {"year": end[0]} if not end[1] else {"year": end[0], "month": end[1]}
        write(DATA / "entities" / "events" / f"{eid[2:]}.yaml", obj)


# 地点
PLACES = [
    ("pl_beiping_zhudi", "北平/北京", "北京", "北京", 39.91, 116.40, "capital", [], "明都"),
    ("pl_nanjing_ming2", "南京/应天", "南京", "江苏", 32.04, 118.78, "capital", [], "明初都/南明"),
    ("pl_haozhou_xu", "濠州", "凤阳", "安徽", 32.86, 117.56, "birthplace", [], "朱元璋/徐达籍贯"),
    ("pl_haozhou_chang", "濠州", "凤阳", "安徽", 32.86, 117.56, "birthplace", [], "常遇春籍贯"),
    ("pl_qingtian_liu", "青田", "青田", "浙江", 28.14, 120.29, "birthplace", [], "刘基籍贯"),
    ("pl_dingyuan_li", "定远", "定远", "安徽", 32.53, 117.68, "birthplace", [], "李善长籍贯"),
    ("pl_dingyuan_lan", "定远", "定远", "安徽", 32.53, 117.68, "birthplace", [], "蓝玉籍贯"),
    ("pl_changzhou_yao", "长洲", "苏州", "江苏", 31.30, 120.62, "birthplace", [], "姚广孝籍贯"),
    ("pl_qiantang_yu", "钱塘", "杭州", "浙江", 30.27, 120.16, "birthplace", [], "于谦籍贯"),
    ("pl_yuyao_wang", "余姚", "余姚", "浙江", 30.04, 121.15, "birthplace", [], "王守仁籍贯"),
    ("pl_jiangling_zhang", "江陵", "荆州", "湖北", 30.33, 112.24, "birthplace", [], "张居正籍贯"),
    ("pl_qiongshan_hai", "琼山", "海口", "海南", 19.90, 110.35, "birthplace", [], "海瑞籍贯"),
    ("pl_dengzhou_qi", "登州", "蓬莱", "山东", 37.81, 120.76, "birthplace", [], "戚继光籍贯"),
    ("pl_fenyi_yan", "分宜", "分宜", "江西", 27.81, 114.69, "birthplace", [], "严嵩籍贯"),
    ("pl_hejian_wei", "河间", "河间", "河北", 38.45, 116.10, "birthplace", [], "魏忠贤籍贯"),
    ("pl_mizhi_li", "米脂", "米脂", "陕西", 37.78, 110.17, "birthplace", [], "李自成籍贯"),
    ("pl_dingbian_zhang", "定边", "定边", "陕西", 37.59, 107.60, "birthplace", [], "张献忠籍贯"),
    ("pl_hetuala_dor", "赫图阿拉", "新宾", "辽宁", 41.71, 125.03, "birthplace", [], "努尔哈赤/皇太极/多尔衮籍贯"),
    ("pl_gaoyou_wu", "高邮", "高邮", "江苏", 32.78, 119.45, "birthplace", [], "吴三桂籍贯"),
    ("pl_xiangfu_shi", "祥符", "开封", "河南", 34.80, 114.31, "birthplace", [], "史可法籍贯"),
    ("pl_nan_an_zheng", "南安", "南安", "福建", 24.96, 118.39, "birthplace", [], "郑成功籍贯"),
    ("pl_shenyang_qing", "盛京/沈阳", "沈阳", "辽宁", 41.81, 123.43, "capital", [], "清入关前都"),
    ("pl_beijing_qing", "北京", "北京", "北京", 39.91, 116.40, "capital", [], "清代都"),
    ("pl_beijing_qing_heshen", "北京", "北京", "北京", 39.91, 116.40, "birthplace", [], "和珅"),
    ("pl_houguan_lin", "侯官", "福州", "福建", 26.07, 119.30, "birthplace", [], "林则徐籍贯"),
    ("pl_xiangxiang_zeng", "湘乡", "湘乡", "湖南", 27.74, 112.51, "birthplace", [], "曾国藩籍贯"),
    ("pl_xiangyin_zuo", "湘阴", "湘阴", "湖南", 28.69, 112.86, "birthplace", [], "左宗棠籍贯"),
    ("pl_hefei_li", "合肥", "合肥", "安徽", 31.82, 117.27, "birthplace", [], "李鸿章籍贯"),
    ("pl_nanpi_zhang", "南皮", "南皮", "河北", 38.02, 116.84, "birthplace", [], "张之洞籍贯"),
    ("pl_xiangcheng_yuan", "项城", "项城", "河南", 33.40, 114.91, "birthplace", [], "袁世凯籍贯"),
    ("pl_beijing_qing_cixi", "北京", "北京", "北京", 39.91, 116.40, "birthplace", [], "慈禧"),
    ("pl_huaxian_hong", "花县", "广州花都", "广东", 23.40, 113.22, "birthplace", [], "洪秀全籍贯"),
    ("pl_guiping_yang", "桂平", "桂平", "广西", 23.39, 110.08, "birthplace", [], "杨秀清籍贯"),
    ("pl_guiping_shi", "桂平", "桂平", "广西", 23.39, 110.08, "birthplace", [], "石达开籍贯"),
    ("pl_luan_han", "栾城", "栾城", "河北", 37.91, 114.65, "birthplace", [], "韩山童籍贯"),
    ("pl_yingzhou_liu", "颍州", "阜阳", "安徽", 32.89, 115.82, "birthplace", [], "刘福通籍贯"),
    ("pl_qishui_chen", "蕲水", "浠水", "湖北", 30.46, 115.27, "birthplace", [], "陈友谅籍贯"),
    ("pl_dongtai_zhang", "东台", "东台", "江苏", 32.85, 120.32, "birthplace", [], "张士诚籍贯"),
    ("pl_dadu_yuan", "大都", "北京", "北京", 39.91, 116.40, "capital", [], "元都"),
    ("pl_dadu_yuan_tuotuo", "大都", "北京", "北京", 39.91, 116.40, "birthplace", [], "脱脱"),
    ("pl_poyanghu", "鄱阳湖", "鄱阳湖", "江西", 29.10, 116.30, "battlefield", [], "1363 鄱阳湖之战"),
    ("pl_tumubao", "土木堡", "怀来", "河北", 40.40, 115.50, "battlefield", [], "1449 土木堡之变"),
    ("pl_sarhu", "萨尔浒", "抚顺", "辽宁", 41.80, 124.10, "battlefield", [], "1619 萨尔浒之战"),
    ("pl_ningyuan", "宁远", "兴城", "辽宁", 40.60, 120.80, "battlefield", [], "1626 宁远之战"),
    ("pl_shanhaiguan", "山海关", "秦皇岛", "河北", 40.00, 119.76, "battlefield", [], "1644 山海关之战"),
    ("pl_kunming_wu", "昆明", "昆明", "云南", 25.04, 102.71, "city", [], "三藩之乱吴三桂都"),
    ("pl_taiwan_qing", "台湾", "台北", "台湾", 25.03, 121.56, "region", [], "1683 收台湾"),
    ("pl_guangzhou_ya", "广州", "广州", "广东", 23.13, 113.27, "battlefield", [], "1839 虎门销烟"),
    ("pl_jintian_taiping", "金田村", "桂平金田", "广西", 23.39, 110.10, "battlefield", [], "1851 金田起义"),
    ("pl_tianjing_taiping", "天京", "南京", "江苏", 32.04, 118.78, "capital", [], "太平天国都"),
    ("pl_korea_jia_wu", "朝鲜", "首尔", "韩国", 37.57, 126.98, "battlefield", [], "甲午战争"),
    ("pl_huang_hai", "黄海", "黄海", "黄海", 36.00, 124.00, "battlefield", [], "黄海海战"),
    ("pl_wuchang_xinhai", "武昌", "武汉", "湖北", 30.55, 114.30, "battlefield", [], "1911 武昌起义"),
    ("pl_nanjing_minguo", "南京", "南京", "江苏", 32.04, 118.78, "capital", [], "民国都"),
    ("pl_dongjing_tongmeng", "东京", "东京", "日本", 35.68, 139.76, "city", [], "同盟会成立"),
    ("pl_wuxi_donglin", "无锡", "无锡", "江苏", 31.49, 120.31, "city", [], "东林书院"),
    ("pl_liujiagang", "刘家港", "太仓", "江苏", 31.50, 121.10, "city", [], "郑和出发港"),
    ("pl_fuzhou_longwu", "福州", "福州", "福建", 26.08, 119.30, "capital", [], "隆武都"),
    ("pl_zhaoqing_yongli", "肇庆", "肇庆", "广东", 23.05, 112.44, "capital", [], "永历都"),

    # Polity stubs for some events
    ("pl_waci", "瓦剌", "蒙古高原", "蒙古", 47.92, 106.92, "region", [], "瓦剌蒙古"),
    ("pl_houjin_sarhu", "建州", "新宾", "辽宁", 41.71, 125.03, "region", [], "后金"),
    ("pl_ying", "英国", "伦敦", "英国", 51.51, -0.13, "region", [], "英帝国"),
    ("pl_rib", "日本", "东京", "日本", 35.68, 139.76, "region", [], "明治日本"),
]
def gen_places():
    for tup in PLACES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat, "description": desc,
            "sources": ["明史·地理志", "清史稿·地理志", "元史·地理志", "中国历史地图集"],
        }
        if aliases:
            obj["aliases"] = aliases
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# 补充 polity stub
POLITY_STUBS = [
    ("k_ming", "明", "Ming", "#c0392b", (1368, 1), (1644, 3), "p_zhuyuanzhang", "pl_beijing_qing", "k_yuan_pre", "k_qing",
     "明朝。朱元璋建。1368 北伐克大都。1644 李自成入京,崇祯自缢。", "明史"),
    ("k_qing", "清", "Qing", "#1abc9c", (1636, None), (1912, 2), "p_huangtaiji", "pl_beijing_qing", "k_ming", "k_minguo",
     "清朝。1636 皇太极改国号。1644 入关。1912 逊位,帝制结束。", "清史稿"),
    ("k_houjin", "后金", "Later Jin", "#8e44ad", (1616, None), (1636, None), "p_nuerhaci", "pl_hetuala_dor", None, "k_qing",
     "努尔哈赤建。1636 改国号清。", "清史稿·太祖本纪"),
    ("k_taiping", "太平天国", "Taiping", "#e74c3c", (1851, 1), (1864, 6), "p_hongxiuquan", "pl_tianjing_taiping", None, "k_qing",
     "1851-1864 洪秀全建。1864 湘军破天京。", "清史稿·洪秀全传"),
    ("k_dashun_li", "大顺", "Da Shun", "#d35400", (1644, 3), (1645, None), "p_lizicheng", "pl_beijing_qing", "k_ming", "k_qing",
     "李自成 1644.3 入京建大顺。山海关败。", "明史·流贼传"),
    ("k_wu_zhang", "大顺吴(占位)", None, None, (None, None), (None, None), None, None, None, None, "", []) if False else None,
    ("k_han_chen", "大汉陈(占位)", None, None, (None, None), (None, None), None, None, None, None, "", []) if False else None,
]
POLITY_STUBS = [p for p in POLITY_STUBS if p is not None and not (p[0].endswith(("_zhang", "_chen")))]
def gen_polity_stubs():
    for tup in POLITY_STUBS:
        pid, name, en, color, founded, ended, founder, capital, supplanted, ended_by, desc, src = tup
        obj = {
            "id": pid, "type": "Polity", "name": name, "name_en": en, "color": color,
            "founded": {"year": founded[0]} if not founded[1] else {"year": founded[0], "month": founded[1]},
            "ended": {"year": ended[0]} if not ended[1] else {"year": ended[0], "month": ended[1]},
            "capital": capital, "description": desc, "sources": src.split(";") if isinstance(src, str) else src,
        }
        if founder: obj["founder"] = founder
        if supplanted: obj["supplanted"] = supplanted
        if ended_by: obj["ended_by"] = ended_by
        write(DATA / "entities" / "polities" / f"{pid[2:]}.yaml", obj)


# 关系
RELATIONS = [
    # 元朝皇帝
    ("p_hubilai", "p_tiemur", "father_of", 1265, None, None, None, None),
    ("p_tiemur", "d_yuan", "succeeded_by", 1294, None, 1307, None, None),
    ("p_a_yu", "d_yuan", "succeeded_by", 1311, None, 1320, None, None),
    ("p_tuogantimur", "d_yuan", "succeeded_by", 1333, None, 1368, None, "末代"),
    ("p_tuotuo_yuan", "p_tuogantimur", "served_under", 1340, None, 1356, None, None),
    ("p_tuotuo_yuan", "e_hongjinjun_qiyi", "participated_in", 1351, None, None, None, "镇压"),

    # 元末群雄
    ("p_hanshantong", "p_liufutong", "allied_with", 1351, None, 1351, None, "红巾"),
    ("p_hanshantong", "e_hongjinjun_qiyi", "participated_in", 1351, None, 1351, None, "领袖"),
    ("p_liufutong", "e_hongjinjun_qiyi", "participated_in", 1351, None, 1363, None, None),
    ("p_chenyouliang", "b_poyanghu", "led", 1363, 8, None, None, "战败身死"),
    ("p_zhuyuanzhang", "b_poyanghu", "led", 1363, 8, None, None, "胜"),

    # 明开国
    ("p_zhuyuanzhang", "k_ming", "founded", 1368, 1, None, None, "都南京"),
    ("p_zhuyuanzhang", "d_yuan", "usurped", 1368, None, None, None, "驱逐元廷"),
    ("p_zhuyuanzhang", "p_xuda", "served_under", 1353, None, 1385, None, None),
    ("p_zhuyuanzhang", "p_changyuchun", "served_under", 1355, None, 1369, None, None),
    ("p_zhuyuanzhang", "p_liuji", "served_under", 1360, None, 1375, None, "谋臣"),
    ("p_zhuyuanzhang", "p_lishanchang", "served_under", 1354, None, 1390, None, None),
    ("p_zhuyuanzhang", "f_huaixi_ji", "leader_of", 1352, None, 1398, None, None),

    # 明帝系
    ("p_zhuyuanzhang", "p_jianwen", "grandfather_of", 1377, None, None, None, "懿文太子朱标早卒"),
    ("p_jianwen", "k_ming", "succeeded_by", 1398, None, 1402, None, None),
    ("p_yongle", "p_jianwen", "usurped", 1402, 7, None, None, "靖难"),
    ("p_yongle", "k_ming", "succeeded_by", 1402, 7, 1424, 7, "成祖"),
    ("p_zhuyuanzhang", "p_yongle", "father_of", 1360, None, None, None, "第四子"),
    ("p_yongle", "p_hongxi", "father_of", 1378, None, None, None, None),
    ("p_hongxi", "k_ming", "succeeded_by", 1424, None, 1425, None, "仁宗"),
    ("p_hongxi", "p_xuande", "father_of", 1399, None, None, None, None),
    ("p_xuande", "k_ming", "succeeded_by", 1425, None, 1435, None, "宣宗"),
    ("p_xuande", "p_zhengtong", "father_of", 1427, None, None, None, None),
    ("p_zhengtong", "k_ming", "succeeded_by", 1435, None, 1449, 9, None),
    ("p_zhengtong", "e_tumubian", "participated_in", 1449, 9, None, None, "被俘"),
    ("p_jingtai", "k_ming", "succeeded_by", 1449, None, 1457, None, "代宗"),
    ("p_yuqian", "p_jingtai", "served_under", 1449, None, 1457, None, None),
    ("p_yuqian", "e_beijing_bao_wei", "led", 1449, 10, None, None, None),
    ("p_zhengtong", "p_jingtai", "sibling_of", None, None, None, None, "兄弟"),
    ("p_zhengtong", "e_duomen_zhibian", "participated_in", 1457, None, None, None, "复辟"),
    ("p_zhengtong", "p_yuqian", "killed", 1457, None, None, None, "夺门后诛"),
    ("p_jingtai", "p_zhengtong", "succeeded_by", 1457, None, 1464, None, "复辟"),
    ("p_zhengtong", "p_chenghua", "father_of", 1447, None, None, None, None),
    ("p_chenghua", "k_ming", "succeeded_by", 1464, None, 1487, None, None),
    ("p_chenghua", "p_hongzhi", "father_of", 1470, None, None, None, None),
    ("p_hongzhi", "k_ming", "succeeded_by", 1487, None, 1505, None, None),
    ("p_hongzhi", "p_zhengde", "father_of", 1491, None, None, None, None),
    ("p_zhengde", "k_ming", "succeeded_by", 1505, None, 1521, None, None),
    ("p_zhengde", "p_jiajing", "sibling_of", None, None, None, None, "堂弟入继"),
    ("p_jiajing", "k_ming", "succeeded_by", 1521, None, 1567, 1, "世宗"),
    ("p_jiajing", "e_daliyi", "participated_in", 1521, None, 1524, None, None),
    ("p_jiajing", "e_gengxu_zhibian", "participated_in", 1550, None, None, None, None),
    ("p_jiajing", "p_yansong", "served_under", 1542, None, 1562, None, None),
    ("p_jiajing", "p_hairui", "rival_of", 1566, None, None, None, "海瑞上疏"),
    ("p_jiajing", "p_longqing", "father_of", 1537, None, None, None, None),
    ("p_longqing", "k_ming", "succeeded_by", 1567, None, 1572, None, None),
    ("p_longqing", "p_wanli", "father_of", 1563, None, None, None, None),
    ("p_wanli", "k_ming", "succeeded_by", 1572, None, 1620, 8, None),
    ("p_wanli", "p_zhangjuzheng", "served_under", 1572, None, 1582, None, None),
    ("p_zhangjuzheng", "e_wang_an_shi_zhang_juzheng", "participated_in", 1573, None, 1582, None, "主导"),
    ("p_qijiguang", "p_zhangjuzheng", "allied_with", 1567, None, 1582, None, "张居正支持戚继光"),
    ("p_wanli", "p_taichang", "father_of", 1582, None, None, None, None),
    ("p_taichang", "k_ming", "succeeded_by", 1620, 8, 1620, 9, "一月天子"),
    ("p_taichang", "p_tianqi", "father_of", 1605, None, None, None, None),
    ("p_tianqi", "k_ming", "succeeded_by", 1620, None, 1627, None, None),
    ("p_tianqi", "p_weizhongxian", "served_under", 1620, None, 1627, None, "魏忠贤专权"),
    ("p_weizhongxian", "f_yandang", "leader_of", 1620, None, 1627, None, None),
    ("p_tianqi", "p_chongzhen", "sibling_of", None, None, None, None, "兄弟"),
    ("p_chongzhen", "k_ming", "succeeded_by", 1627, None, 1644, 3, "末代"),
    ("p_chongzhen", "p_weizhongxian", "killed", 1627, None, None, None, "诛阉党"),

    # 东林党
    ("p_yandang_donglin_link", "占位", None, None, None, None, None, None) if False else None,
    ("f_donglin_dang", "f_yandang", "rival_of", 1620, None, 1627, None, "东林 vs 阉党"),

    # 明末农民起义
    ("p_lizicheng", "e_xin_hai_ge_ming", "participated_in", None, None, None, None, None) if False else None,
    ("p_lizicheng", "k_dashun_li", "founded", 1644, 3, None, None, "大顺"),
    ("p_lizicheng", "b_shanhai_guan", "led", 1644, 5, None, None, "败"),
    ("p_wusan_gui", "b_shanhai_guan", "participated_in", 1644, 5, None, None, "引清入关"),
    ("p_duoergun", "b_shanhai_guan", "led", 1644, 5, None, None, "胜方"),
    ("p_duoergun", "p_wusan_gui", "allied_with", 1644, 5, None, None, "联合灭李"),

    # 后金/清初
    ("p_nuerhaci", "k_houjin", "founded", 1616, None, None, None, None),
    ("p_nuerhaci", "b_sarhu", "led", 1619, 4, None, None, "胜"),
    ("p_nuerhaci", "b_ningyuan", "led", 1626, None, None, None, "战败受创"),
    ("p_huangtaiji", "p_nuerhaci", "father_of", None, None, None, None, "第八子"),
    ("p_huangtaiji", "k_houjin", "succeeded_by", 1626, None, 1636, None, None),
    ("p_huangtaiji", "k_qing", "founded", 1636, None, None, None, "改国号清"),
    ("p_huangtaiji", "p_shunzhi", "father_of", 1638, None, None, None, None),
    ("p_duoergun", "p_nuerhaci", "father_of", None, None, None, None, "第十四子"),
    ("p_shunzhi", "k_qing", "succeeded_by", 1644, None, 1661, None, "入关定鼎"),
    ("p_shunzhi", "p_duoergun", "served_under", 1644, None, 1650, None, "摄政"),

    # 清帝系
    ("p_shunzhi", "p_kangxi", "father_of", 1654, None, None, None, None),
    ("p_kangxi", "k_qing", "succeeded_by", 1661, None, 1722, None, "圣祖 61 年"),
    ("p_kangxi", "e_kangxi_ping_sanfan", "participated_in", 1673, 12, 1681, 10, "主导"),
    ("p_kangxi", "e_shou_taiwan", "participated_in", 1683, None, None, None, None),
    ("p_kangxi", "p_yongzheng", "father_of", 1678, None, None, None, None),
    ("p_yongzheng", "k_qing", "succeeded_by", 1722, None, 1735, None, None),
    ("p_yongzheng", "e_yongzheng_gaige", "participated_in", 1723, None, 1735, None, "主导"),
    ("p_yongzheng", "p_qianlong", "father_of", 1711, None, None, None, None),
    ("p_qianlong", "k_qing", "succeeded_by", 1735, None, 1796, None, None),
    ("p_qianlong", "e_shiquan_wugong", "participated_in", 1755, None, 1792, None, "主导"),
    ("p_qianlong", "p_heshen", "served_under", 1775, None, 1799, None, "和珅专权"),
    ("p_qianlong", "p_jiaqing", "father_of", 1760, None, None, None, None),
    ("p_jiaqing", "k_qing", "succeeded_by", 1796, None, 1820, None, None),
    ("p_jiaqing", "p_heshen", "killed", 1799, None, None, None, "诛和珅"),
    ("p_jiaqing", "p_daoguang", "father_of", 1782, None, None, None, None),
    ("p_daoguang", "k_qing", "succeeded_by", 1820, None, 1850, None, None),
    ("p_daoguang", "e_ya_pian_zhanzheng", "participated_in", 1840, 6, 1842, 8, None),
    ("p_linzexu", "p_daoguang", "served_under", 1838, None, 1840, None, None),
    ("p_linzexu", "e_ya_pian_zhanzheng", "participated_in", 1839, 6, None, None, "虎门销烟"),
    ("p_daoguang", "p_xianfeng", "father_of", 1831, None, None, None, None),
    ("p_xianfeng", "k_qing", "succeeded_by", 1850, None, 1861, None, None),
    ("p_xianfeng", "e_taiping_tian_guo", "participated_in", 1851, None, 1861, None, None),
    ("p_xianfeng", "p_cixi", "spouse_of", None, None, None, None, "妃"),
    ("p_xianfeng", "p_tongzhi", "father_of", 1856, None, None, None, None),
    ("p_tongzhi", "k_qing", "succeeded_by", 1861, None, 1875, None, None),
    ("p_cixi", "p_tongzhi", "mother_of", None, None, None, None, None),
    ("p_cixi", "p_guangxu", "aunt_of", None, None, None, None, None) if False else None,
    ("p_guangxu", "k_qing", "succeeded_by", 1875, None, 1908, None, None),
    ("p_cixi", "p_guangxu", "rival_of", 1898, None, 1908, None, "戊戌变法vs政变"),
    ("p_guangxu", "e_jia_wu_zhanzheng", "participated_in", 1894, 7, 1895, 4, None),
    ("p_lihongzhang", "e_jia_wu_zhanzheng", "participated_in", 1894, 7, None, None, "北洋主导"),
    ("p_guangxu", "e_wu_xu_bian_fa", "participated_in", 1898, 6, 1898, 9, "主导"),
    ("p_cixi", "e_wu_xu_bian_fa", "participated_in", 1898, 9, None, None, "政变"),
    ("p_guangxu", "e_gengzi_qiyi", "participated_in", 1900, None, None, None, "西狩"),
    ("p_cixi", "e_gengzi_qiyi", "participated_in", 1900, None, None, None, "宣战"),
    ("p_guangxu", "p_xuantong", "uncle_of", None, None, None, None, None) if False else None,
    ("p_xuantong", "k_qing", "succeeded_by", 1908, None, 1912, 2, "末代"),
    ("p_xuantong", "e_xin_hai_ge_ming", "participated_in", 1911, 10, 1912, 2, "退位"),

    # 洋务 / 名臣
    ("p_zengguofan", "f_xiangjun", "leader_of", 1853, None, 1872, None, None),
    ("p_zengguofan", "e_taiping_tian_guo", "participated_in", 1853, None, 1864, 6, "平太平"),
    ("p_zengguofan", "e_yang_wu_yun_dong", "participated_in", 1861, None, 1872, None, None),
    ("p_zuozongtang", "p_zengguofan", "allied_with", None, None, None, None, "同为湘军系"),
    ("p_lihongzhang", "p_zengguofan", "mentored_by", None, None, None, None, "李鸿章是曾国藩门生"),
    ("p_lihongzhang", "f_huaijun_bei_yang", "leader_of", 1862, None, 1901, None, None),
    ("p_zhangzhidong", "e_yang_wu_yun_dong", "participated_in", 1884, None, 1909, None, None),
    ("p_yuanshikai", "f_huaijun_bei_yang", "leader_of", 1895, None, 1916, None, None),
    ("p_yuanshikai", "e_xin_hai_ge_ming", "participated_in", 1911, 10, None, None, "北洋系核心"),

    # 太平天国
    ("p_hongxiuquan", "k_taiping", "founded", 1851, 1, None, None, None),
    ("p_hongxiuquan", "f_taiping", "leader_of", 1851, None, 1864, None, None),
    ("p_yangxiuqing", "p_hongxiuquan", "served_under", 1851, None, 1856, None, "东王"),

    # 政权更替
    ("k_ming", "k_qing", "destroyed_by", 1644, 3, None, None, None),
    ("k_qing", "k_minguo", "destroyed_by", 1912, 2, None, None, None),
    ("d_yuan", "k_ming", "destroyed_by", 1368, None, None, None, None),
    ("d_ming", "k_ming", "includes", 1368, 1, 1644, 3, None),
    ("d_qing", "k_qing", "includes", 1636, None, 1912, 2, None),

    # 因果链
    ("e_hongjinjun_qiyi", "k_ming", "preceded_by", None, None, None, None, "红巾起义→明建立"),
    ("e_jingnan_zhiyi", "e_zhenghe_xiaxiyang", "preceded_by", None, None, None, None, "靖难→永乐朝"),
    ("e_tumubian", "e_duomen_zhibian", "preceded_by", None, None, None, None, "土木堡→夺门"),
    ("e_daliyi", "e_yansong_zhuangquan", "preceded_by", None, None, None, None, None) if False else None,
    ("e_ya_pian_zhanzheng", "e_taiping_tian_guo", "preceded_by", None, None, None, None, "鸦片战争→太平天国"),
    ("e_yang_wu_yun_dong", "e_jia_wu_zhanzheng", "preceded_by", None, None, None, None, "洋务→甲午破产"),
    ("e_jia_wu_zhanzheng", "e_wu_xu_bian_fa", "preceded_by", None, None, None, None, "甲午→维新"),
    ("e_gengzi_qiyi", "e_xin_hai_ge_ming", "preceded_by", None, None, None, None, "庚子→革命"),
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
    out = DATA / "relations" / "yuan_ming_qing.yaml"
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(deduped, f, allow_unicode=True, sort_keys=False)
    print(f"  ✓ {len(deduped)} relations → data/relations/yuan_ming_qing.yaml")


if __name__ == "__main__":
    print(f"→ Phase 14: Yuan / Ming / Qing")
    gen_places()
    print(f"  ✓ {len(PLACES)} places")
    gen_polity_stubs()
    print(f"  ✓ {len(POLITY_STUBS)} polity stubs")
    gen_polities()
    print(f"  ✓ {len(POLITIES)} polities (民国等)")
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
