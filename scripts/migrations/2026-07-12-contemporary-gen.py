#!/usr/bin/env python3
"""生成现代史(1949-今)实体。客观中性、带出处。写 data/entities/{persons,events}/ + relations/contemporary.yaml。"""
import os
BASE = "/Users/rick/ZCodeProject/history-kb/.claude/worktrees/project-version-roadmap-872b4e"
SRC_PRC = ["中华人民共和国史", "当代中国史"]

def y(v):
    return "{year: %d}" % v

# (id, name, born, died, roles, importance, bio)  —— bio 客观中性,仅陈述职务/经历
PERSONS = [
 ("p_mao_zedong","毛泽东",1893,1976,["civil_official"],1,"湖南湘潭人。中国共产党主要领导人，中华人民共和国主要缔造者，1949-1976年任中共中央主席，1949-1959年任中央人民政府主席、国家主席。"),
 ("p_zhou_enlai","周恩来",1898,1976,["civil_official"],1,"江苏淮安人。1949-1976年任国务院总理(政务院总理),长期兼任外交部长,主持政府与外交工作。"),
 ("p_liu_shaoqi","刘少奇",1898,1969,["civil_official"],2,"湖南宁乡人。1959-1968年任中华人民共和国主席。文化大革命中被打倒,1969年病逝,1980年平反。"),
 ("p_zhu_de","朱德",1886,1976,["general"],2,"四川仪陇人。中国人民解放军主要缔造者之一,中华人民共和国元帅,1959-1976年任全国人大常委会委员长。"),
 ("p_deng_xiaoping","邓小平",1904,1997,["civil_official"],1,"四川广安人。改革开放的主要决策者,1978年起主导国家改革开放政策,曾任中央军委主席、中顾委主任等职。"),
 ("p_chen_yun","陈云",1905,1995,["civil_official"],2,"上海青浦人。长期主管经济工作,曾任国务院副总理、中央纪委第一书记等职。"),
 ("p_peng_dehuai","彭德怀",1898,1974,["general"],2,"湖南湘潭人。中华人民共和国元帅,抗美援朝时任中国人民志愿军司令员,曾任国防部长。1959年后去职,文革中受迫害,1974年病逝,后平反。"),
 ("p_lin_biao","林彪",1907,1971,["general"],2,"湖北黄冈人。中华人民共和国元帅。1971年9月13日在外蒙古温都尔汗因飞机失事身亡。"),
 ("p_chen_yi","陈毅",1901,1972,["general","literatus"],2,"四川乐至人。中华人民共和国元帅,曾任上海市长、国务院副总理兼外交部长。"),
 ("p_ye_jianying","叶剑英",1897,1986,["general"],2,"广东梅县人。中华人民共和国元帅,1978-1983年任全国人大常委会委员长。"),
 ("p_song_qingling","宋庆龄",1893,1981,["civil_official"],2,"广东文昌人,生于上海。孙中山夫人,曾任中华人民共和国副主席、名誉主席。"),
 ("p_hua_guofeng","华国锋",1921,2008,["civil_official"],2,"山西交城人。1976-1981年间先后任中共中央主席、国务院总理、中央军委主席。"),
 ("p_hu_yaobang","胡耀邦",1915,1989,["civil_official"],2,"湖南浏阳人。1981-1987年任中共中央主席、总书记。1989年病逝。"),
 ("p_li_xiannian","李先念",1909,1992,["civil_official"],2,"湖北红安人。1983-1988年任中华人民共和国主席。"),
 # 科学文化(争议少)
 ("p_qian_xuesen","钱学森",1911,2009,["scholar"],1,"浙江杭州人。空气动力学家,中国航天事业奠基人之一,'两弹一星'元勋。"),
 ("p_deng_jiaxian","邓稼先",1924,1986,["scholar"],2,"安徽怀宁人。核物理学家,中国核武器研制主要组织者之一,'两弹一星'元勋。"),
 ("p_hua_luogeng","华罗庚",1910,1985,["scholar"],2,"江苏金坛人。数学家,在数论、多复变函数论等领域有重要贡献。"),
 ("p_qian_sanqiang","钱三强",1913,1992,["scholar"],2,"浙江湖州人,生于绍兴。核物理学家,'两弹一星'元勋。"),
 ("p_ba_jin","巴金",1904,2005,["literatus"],2,"四川成都人。作家,著有《家》《春》《秋》等,曾任中国作家协会主席。"),
 ("p_qian_zhongshu","钱钟书",1910,1998,["scholar","literatus"],2,"江苏无锡人。学者、作家,著有《围城》《管锥编》等。"),
 ("p_ji_xianlin","季羡林",1911,2009,["scholar"],2,"山东临清人。语言学家、东方学家,精通梵语等,长期任教于北京大学。"),
 ("p_yuan_longping","袁隆平",1930,2021,["scholar"],1,"生于北京,籍贯江西德安。农学家,杂交水稻研究奠基人之一。"),
]

# (id, name, date, end, category, location_id, description, impact)
EVENTS = [
 ("e_prc_founding","中华人民共和国成立",1949,None,"other",None,"1949年10月1日,在北京天安门广场举行典礼,宣告中华人民共和国成立。","结束了近代以来的长期战乱与分裂状态,确立新的国家政权。"),
 ("e_kang_mei_yuan_chao","抗美援朝",1950,1953,"war",None,"1950年10月中国人民志愿军入朝,与朝鲜方面共同对以美国为首的联合国军作战,1953年7月签订《朝鲜停战协定》。","朝鲜半岛恢复战前分界线态势。"),
 ("e_yi_wu_jihua","第一个五年计划",1953,1957,"reform",None,"1953-1957年实施的国民经济发展计划,以发展重工业为重点,建设一批工业项目。","初步建立起工业化基础。"),
 ("e_da_yue_jin","大跃进",1958,1960,"reform",None,"1958-1960年开展的以大规模增产为目标的经济运动。","经济发展出现严重困难,后进行调整。"),
 ("e_wen_hua_da_ge_ming","文化大革命",1966,1976,"other",None,"1966年5月至1976年10月的政治运动。1981年中共中央《关于建国以来党的若干历史问题的决议》对其作出评价。","对国家政治、经济、文化、社会造成深远影响。"),
 ("e_lianheguo_xiwei","恢复联合国合法席位",1971,None,"diplomacy",None,"1971年10月25日,第26届联合国大会通过第2758号决议,恢复中华人民共和国在联合国的合法席位。","中华人民共和国进入联合国等国际组织。"),
 ("e_gaige_kaifang","改革开放",1978,None,"reform",None,"1978年12月中共十一届三中全会后,中国开始实行改革开放政策,推进经济体制改革与对外开放。","国民经济持续快速增长,社会面貌发生深刻变化。"),
 ("e_jingji_tequ","经济特区设立",1980,None,"reform",None,"1980年,深圳、珠海、汕头、厦门设立经济特区,实行特殊经济政策。","成为对外开放的窗口与试验区。"),
 ("e_zhongmei_jianjiao","中美建交",1979,None,"diplomacy",None,"1979年1月1日,中华人民共和国与美利坚合众国正式建立外交关系。","中美关系正常化。"),
 ("e_xianggang_huigui","香港回归",1997,None,"other",None,"1997年7月1日,中国政府对香港恢复行使主权,设立香港特别行政区。","结束英国对香港的管治。"),
 ("e_aomen_huigui","澳门回归",1999,None,"other",None,"1999年12月20日,中国政府对澳门恢复行使主权,设立澳门特别行政区。","结束葡萄牙对澳门的管治。"),
 ("e_jiaru_wto","加入世界贸易组织",2001,None,"diplomacy",None,"2001年12月11日,中国正式加入世界贸易组织(WTO)。","进一步融入全球贸易体系。"),
 ("e_shenzhou5","神舟五号载人航天",2003,None,"other",None,"2003年10月15日,航天员杨利伟乘神舟五号飞船进入太空,成为中国首次载人航天飞行。","中国成为第三个独立掌握载人航天技术的国家。"),
 ("e_beijing_aoyun","北京奥运会",2008,None,"other",None,"2008年8月8日至24日,第29届夏季奥林匹克运动会在北京举行。","中国首次举办夏季奥运会。"),
]

# (from, type, to, note)
RELATIONS = [
 ("p_mao_zedong","led","e_prc_founding","1949年10月1日在天安门宣告中华人民共和国成立"),
 ("p_deng_xiaoping","led","e_gaige_kaifang","改革开放主要决策者,十一届三中全会后主导政策"),
 ("p_peng_dehuai","led","e_kang_mei_yuan_chao","任中国人民志愿军司令员"),
 ("p_zhou_enlai","participated_in","e_lianheguo_xiwei","主持外交,推动恢复联合国席位"),
 ("p_deng_xiaoping","led","e_jingji_tequ","1980年推动设立深圳等经济特区"),
]

def yaml_person(p):
    id_,name,born,died,roles,imp,bio=p
    L=[f"id: {id_}", f"name: {name}", "type: Person", f"born: {y(born)}"]
    if died: L.append(f"died: {y(died)}")
    L.append("roles:")
    for r in roles: L.append(f"  - {r}")
    L.append(f"importance: {imp}")
    L.append(f"bio: {bio}")
    L.append("sources:")
    for s in SRC_PRC: L.append(f"  - {s}")
    return "\n".join(L)+"\n"

def yaml_event(e):
    id_,name,date,end,cat,loc,desc,impact=e
    L=[f"id: {id_}", f"name: {name}", "type: Event", f"date: {y(date)}"]
    if end: L.append(f"end_date: {y(end)}")
    L.append(f"category: {cat}")
    L.append(f"description: {desc}")
    if impact: L.append(f"impact: {impact}")
    L.append("sources:")
    for s in SRC_PRC: L.append(f"  - {s}")
    return "\n".join(L)+"\n"

np=ne=0
for p in PERSONS:
    open(f"{BASE}/data/entities/persons/{p[0][2:]}.yaml","w").write(yaml_person(p)); np+=1
for e in EVENTS:
    open(f"{BASE}/data/entities/events/{e[0][2:]}.yaml","w").write(yaml_event(e)); ne+=1
# relations file
rl=["relations:"]
for r in RELATIONS:
    rl.append(f"  - from: {r[0]}")
    rl.append(f"    type: {r[1]}")
    rl.append(f"    to: {r[2]}")
    rl.append(f"    note: {r[3]}")
open(f"{BASE}/data/relations/contemporary.yaml","w").write("\n".join(rl)+"\n")
print(f"写入 人物 {np} 事件 {ne} 关系 {len(RELATIONS)}")
