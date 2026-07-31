#!/usr/bin/env python3
# 现当代加密(1949+)。Claude 亲写、中性事实。存在则跳过。yaml.safe_dump 安全转义。
import os, yaml
BASE = "/Users/rick/ZCodeProject/history-kb/.claude/worktrees/project-version-roadmap-872b4e/data"
SRC = ["中华人民共和国史", "当代中国史"]
def y(v): return {"year": v}

# (id, name, born, died|None, roles, imp, bio, life_events|None, extra_sources)
PERSONS = [
 ("p_jiang_zemin","江泽民",1926,2022,["civil_official"],1,
  "江苏扬州人。1989至2002年任中共中央总书记，1993至2003年任国家主席，1989至2004年任中央军委主席。任内提出'三个代表'重要思想，2001年中国加入世界贸易组织。",
  [(1989,"任中共中央总书记"),(1993,"任国家主席"),(2001,"任内中国加入世界贸易组织"),(2022,"逝世")], []),
 ("p_li_peng","李鹏",1928,2019,["civil_official"],2,
  "生于上海，四川成都人。1988至1998年任国务院总理，1998至2003年任全国人大常委会委员长。", None, []),
 ("p_zhu_rongji","朱镕基",1928,None,["civil_official"],2,
  "湖南长沙人。1998至2003年任国务院总理，主持国有企业、分税制、住房与金融体制改革，推动中国加入世界贸易组织的谈判。", None, []),
 ("p_hu_jintao","胡锦涛",1942,None,["civil_official"],1,
  "安徽绩溪人，生于江苏泰州。2002至2012年任中共中央总书记，2003至2013年任国家主席，2004至2012年任中央军委主席。任内提出科学发展观。",
  [(2002,"任中共中央总书记"),(2003,"任国家主席"),(2012,"中共十八大后卸任")], []),
 ("p_wen_jiabao","温家宝",1942,None,["civil_official"],2,
  "天津人。2003至2013年任国务院总理，任内应对非典疫情、汶川地震及国际金融危机。", None, []),
 ("p_zhao_ziyang","赵紫阳",1919,2005,["civil_official"],2,
  "河南滑县人。1980至1987年任国务院总理，1987至1989年任中共中央总书记，推动经济体制改革。1989年政治风波中去职，此后离开公众视野。", None, []),
 ("p_tu_youyou","屠呦呦",1930,None,["scholar"],1,
  "浙江宁波人。药学家，发现青蒿素及双氢青蒿素用于治疗疟疾。2015年获诺贝尔生理学或医学奖，为首位获科学类诺贝尔奖的中国本土科学家。",
  [(1972,"所在团队分离出青蒿素"),(2015,"获诺贝尔生理学或医学奖")], ["诺贝尔奖官方资料"]),
 ("p_mo_yan","莫言",1955,None,["literatus"],2,
  "本名管谟业，山东高密人。作家，著有《红高粱家族》《生死疲劳》《蛙》等。2012年获诺贝尔文学奖。", None, ["诺贝尔奖官方资料"]),
 ("p_yu_min","于敏",1926,2019,["scholar"],2,
  "河北宁河人。核物理学家，中国氢弹研制的主要理论奠基者之一，'两弹一星'功勋奖章及国家最高科学技术奖获得者。", None, []),
 ("p_sun_jiadong","孙家栋",1929,None,["scholar"],2,
  "辽宁复县人。航天技术专家，中国第一颗人造卫星'东方红一号'技术负责人之一，北斗导航与探月工程总设计师，'两弹一星'功勋奖章获得者。", None, []),
 ("p_chen_jingrun","陈景润",1933,1996,["scholar"],2,
  "福建福州人。数学家，在哥德巴赫猜想研究中证明'1+2'（陈氏定理），为该领域重要成果。", None, []),
 ("p_jin_yong","金庸",1924,2018,["literatus"],2,
  "本名查良镛，浙江海宁人，长期居香港。武侠小说家、《明报》创办人，著有《射雕英雄传》《天龙八部》《笑傲江湖》等，为华语世界影响广泛的通俗文学作家。", None, []),
 ("p_fei_xiaotong","费孝通",1910,2005,["scholar"],3,
  "江苏吴江人。社会学家、人类学家，著有《乡土中国》《江村经济》等，曾任全国人大常委会副委员长、中国民主同盟主席。", None, []),
 ("p_he_long","贺龙",1896,1969,["general"],2,
  "湖南桑植人。中华人民共和国元帅，南昌起义总指挥，中国人民解放军创建人之一，曾任国务院副总理、国家体委主任。文化大革命中受迫害，1969年逝世，后平反。", None, []),
 ("p_nie_rongzhen","聂荣臻",1899,1992,["general"],2,
  "四川江津人。中华人民共和国元帅，曾主持国防科技工作、组织'两弹'研制，任国务院副总理。", None, []),
 ("p_su_yu","粟裕",1907,1984,["general"],2,
  "湖南会同人，侗族。中国人民解放军大将，华东野战军主要指挥员，指挥苏中、豫东、淮海、渡江等战役，后任总参谋长。", None, []),
]

# (id, name, date, end|None, category, description, impact|None, extra_sources)
EVENTS = [
 ("e_tudi_gaige","土地改革",1950,1953,"reform",
  "1950年颁布《中华人民共和国土地改革法》，在新解放区废除地主土地所有制、将土地分配给农民，至1953年基本完成。","改变了农村土地占有关系。",[]),
 ("e_fanyou_yundong","反右运动",1957,None,"purge",
  "1957年，在整风运动基础上开展反右派斗争，大批知识分子、民主人士被划为'右派分子'。1978年后中共中央为绝大多数被划右派者平反改正。","对知识界与政治生活产生长期影响。",[]),
 ("e_sannian_kunnan","三年困难时期",1959,1961,"disaster",
  "1959至1961年，因'大跃进'、人民公社化运动的失误及自然灾害等因素，全国出现严重经济困难与大范围饥荒，人口非正常死亡。","此后国民经济进入调整时期。",[]),
 ("e_diyike_yuanzidan","第一颗原子弹爆炸",1964,None,"other",
  "1964年10月16日，中国在新疆罗布泊成功爆炸第一颗原子弹。","中国成为第五个拥有核武器的国家。",[]),
 ("e_qingdan","第一颗氢弹爆炸",1967,None,"other",
  "1967年6月17日，中国成功进行首次氢弹试验。",None,[]),
 ("e_dongfanghong1","东方红一号卫星",1970,None,"other",
  "1970年4月24日，中国成功发射第一颗人造地球卫星'东方红一号'。","中国成为第五个独立发射人造卫星的国家。",[]),
 ("e_nikesong_fanghua","尼克松访华",1972,None,"diplomacy",
  "1972年2月，美国总统尼克松访问中国，双方在上海发表《联合公报》。","中美关系开始走向正常化。",[]),
 ("e_fensui_siren_bang","粉碎'四人帮'",1976,None,"coup",
  "1976年10月，华国锋、叶剑英等采取行动，逮捕江青、张春桥、姚文元、王洪文，'文化大革命'结束。","国家进入新的历史时期。",[]),
 ("e_zhenli_biaozhun","真理标准问题讨论",1978,None,"culture",
  "1978年，围绕'实践是检验真理的唯一标准'展开全国性讨论。","为改革开放作了思想准备。",[]),
 ("e_1989_fengbo","1989年政治风波",1989,None,"other",
  "1989年4月至6月，北京等城市发生以青年学生为主的大规模示威活动，6月初以军队进入市区、实施戒严结束。",None,[]),
 ("e_nanxun_jianghua","邓小平南方谈话",1992,None,"reform",
  "1992年初，邓小平视察武昌、深圳、珠海、上海等地并发表谈话，强调坚持改革开放。","推动新一轮改革开放。",[]),
 ("e_shichang_jingji","确立社会主义市场经济体制",1992,None,"reform",
  "1992年中共十四大提出建立社会主义市场经济体制的改革目标。","确立经济体制改革的方向。",[]),
 ("e_sanxia_gongcheng","三峡工程",1994,2009,"other",
  "长江三峡水利枢纽工程，1994年正式开工，2003年首批机组发电，2009年基本建成，为大型水利水电与防洪航运工程。",None,[]),
 ("e_deng_shishi","邓小平逝世",1997,None,"other",
  "1997年2月19日，邓小平在北京逝世。",None,[]),
 ("e_feidian_sars","非典型肺炎疫情",2002,2003,"disaster",
  "2002年底至2003年，严重急性呼吸综合征（SARS，非典）在中国及多国传播。","推动公共卫生应急体系建设。",[]),
 ("e_wenchuan_dizhen","汶川地震",2008,None,"disaster",
  "2008年5月12日，四川汶川发生里氏8.0级地震，造成重大人员伤亡与财产损失。",None,[]),
 ("e_shanghai_shibo","上海世博会",2010,None,"other",
  "2010年5月至10月，第41届世界博览会在上海举行，主题为'城市，让生活更美好'。",None,[]),
 ("e_yidai_yilu","一带一路倡议",2013,None,"diplomacy",
  "2013年，中国提出共建'丝绸之路经济带'和'21世纪海上丝绸之路'的合作倡议。",None,[]),
 ("e_tuopin_gongjian","脱贫攻坚",2013,2021,"reform",
  "2013年提出精准扶贫，2020年底宣布现行标准下农村贫困人口全部脱贫，2021年宣布脱贫攻坚战取得全面胜利。",None,[]),
 ("e_covid19","COVID-19疫情",2019,2023,"disaster",
  "2019年底新型冠状病毒感染（COVID-19）疫情出现，其后在全球大流行；中国采取大规模防控措施，2023年初调整防控政策。",None,[]),
 ("e_beijing_dongao","北京冬奥会",2022,None,"other",
  "2022年2月，第24届冬季奥林匹克运动会在北京举行，北京成为首个既举办夏季奥运会又举办冬季奥运会的城市。",None,[]),
]

# (from, type, to, note)
RELATIONS = [
 ("p_zhu_rongji","participated_in","e_jiaru_wto","任国务院总理，主持中国加入世贸组织的谈判"),
 ("p_hua_guofeng","led","e_fensui_siren_bang","1976年10月主持采取行动逮捕'四人帮'"),
 ("p_deng_xiaoping","led","e_nanxun_jianghua","1992年初视察南方并发表谈话，推动改革开放"),
 ("p_wen_jiabao","participated_in","e_wenchuan_dizhen","时任国务院总理，主持抗震救灾"),
 ("p_zhao_ziyang","participated_in","e_1989_fengbo","时任中共中央总书记，风波后去职"),
 ("e_da_yue_jin","led_to","e_sannian_kunnan","大跃进与人民公社化运动的失误为三年困难时期主因之一"),
 ("e_zhenli_biaozhun","led_to","e_gaige_kaifang","真理标准讨论的思想解放为改革开放作准备"),
 ("e_nanxun_jianghua","led_to","e_shichang_jingji","南方谈话推动中共十四大确立社会主义市场经济体制"),
 ("e_nikesong_fanghua","led_to","e_zhongmei_jianjiao","1972年破冰后，1979年中美正式建交"),
]

def person_dict(p):
    id_,name,born,died,roles,imp,bio,les,extra = p
    d = {"id": id_, "type": "Person", "name": name, "born": y(born)}
    if died: d["died"] = y(died)
    d["gender"] = "female" if name in ("屠呦呦",) else "male"
    d["roles"] = roles
    d["importance"] = imp
    d["bio"] = bio
    if les:
        d["life_events"] = [{"year": yr, "event": ev} for (yr, ev) in les]
    d["sources"] = SRC + extra
    return d

def event_dict(e):
    id_,name,date,end,cat,desc,impact,extra = e
    d = {"id": id_, "type": "Event", "name": name, "date": y(date)}
    if end: d["end_date"] = y(end)
    d["category"] = cat
    d["description"] = desc
    if impact: d["impact"] = impact
    d["sources"] = SRC + extra
    return d

def dump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

np=ne=sk=0
for p in PERSONS:
    path=f"{BASE}/entities/persons/{p[0][2:]}.yaml"
    if os.path.exists(path): sk+=1; continue
    dump(path, person_dict(p)); np+=1
for e in EVENTS:
    path=f"{BASE}/entities/events/{e[0][2:]}.yaml"
    if os.path.exists(path): sk+=1; continue
    dump(path, event_dict(e)); ne+=1
rels=[{"from":r[0],"type":r[1],"to":r[2],"note":r[3]} for r in RELATIONS]
dump(f"{BASE}/relations/contemporary_ext.yaml", rels)
print(f"写入 人物 {np} 事件 {ne} 关系 {len(rels)}；跳过(已存在) {sk}")
