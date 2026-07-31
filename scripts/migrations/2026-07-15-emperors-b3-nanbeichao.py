#!/usr/bin/env python3
"""帝王世系 第三批:南北朝(宋齐梁陈 + 北魏/东魏/西魏/北齐/北周)。Claude 亲撰。
护栏:id 已存在但 name 不符 -> 中止(防 p_zhao_yun 式拼音撞车)。"""
import os, sys, yaml
B = "/Users/rick/ZCodeProject/history-kb/.claude/worktrees/project-version-roadmap-872b4e/data/entities/persons"
S_S = ["宋书", "南史", "资治通鉴"]
S_Q = ["南齐书", "南史", "资治通鉴"]
S_L = ["梁书", "南史", "资治通鉴"]
S_C = ["陈书", "南史", "资治通鉴"]
S_W = ["魏书", "北史", "资治通鉴"]
S_BQ = ["北齐书", "北史", "资治通鉴"]
S_BZ = ["周书", "北史", "资治通鉴"]
def y(v): return {"year": v}

# (id, name, title, regime, alias[], born, died, rs, re, imp, bio, sources)
E = [
# ── 刘宋 420-479 ──（刘裕 420-422 已存在）
("p_liu_yifu","刘义符","宋少帝","刘宋",["宋少帝","营阳王"],406,424,422,424,3,"武帝长子。居丧无礼、好狎昵,424年为徐羡之等所废杀。",S_S),
("p_liu_yilong","刘义隆","宋文帝","刘宋",["宋文帝"],407,453,424,453,2,"武帝三子。在位三十年,劝课农桑、轻徭薄赋,史称'元嘉之治'。三次北伐拓跋魏皆败,'元嘉草草,封狼居胥,赢得仓皇北顾'。453年为太子刘劭所弑。",S_S),
("p_liu_jun","刘骏","宋孝武帝","刘宋",["宋孝武帝"],430,464,453,464,3,"文帝三子。讨平弑父之刘劭而立。加强中央集权、削弱宗王,然荒淫奢靡。",S_S),
("p_liu_ziye","刘子业","宋前废帝","刘宋",["前废帝"],449,465,464,465,3,"孝武帝子。凶暴悖乱,屠戮宗室,465年为湘东王刘彧所弑。",S_S),
("p_liu_yu_mingdi","刘彧","宋明帝","刘宋",["宋明帝"],439,472,465,472,3,"文帝十一子。弑前废帝自立。大杀宗室,淮北四州尽失于魏。",S_S),
("p_liu_yu_houfeidi","刘昱","宋后废帝","刘宋",["后废帝","苍梧王"],463,477,472,477,3,"明帝子,十岁即位。暴虐嗜杀,477年为萧道成遣人所弑。",S_S),
("p_liu_zhun","刘准","宋顺帝","刘宋",["宋顺帝"],467,479,477,479,3,"明帝子。萧道成所立。479年禅位于萧道成,刘宋亡,旋被杀。",S_S),
# ── 南齐 479-502 ──
("p_xiao_daocheng","萧道成","齐高帝","南齐",["齐高帝"],427,482,479,482,3,"代宋建齐。行俭约、罢奢费。在位四年而崩。",S_Q),
("p_xiao_ze","萧赜","齐武帝","南齐",["齐武帝"],440,493,482,493,3,"高帝子。承高帝之政,与北魏通好,境内安集,史称'永明之治'。永明文学盛于其时。",S_Q),
("p_xiao_zhaoye","萧昭业","齐郁林王","南齐",["郁林王"],473,494,493,494,3,"武帝孙。奢纵无度,494年为萧鸾所废杀。",S_Q),
("p_xiao_zhaowen","萧昭文","齐海陵王","南齐",["海陵王"],480,494,494,494,3,"武帝孙。萧鸾所立,在位数月被废,旋遇害。",S_Q),
("p_xiao_luan","萧鸾","齐明帝","南齐",["齐明帝"],452,498,494,498,3,"高帝侄。连废二帝自立,大杀高帝、武帝子孙殆尽。",S_Q),
("p_xiao_baojuan","萧宝卷","齐东昏侯","南齐",["东昏侯"],483,501,498,501,3,"明帝子。荒暴嗜杀,诛戮大臣,激起萧衍起兵。501年为其臣所弑。",S_Q),
("p_xiao_baorong","萧宝融","齐和帝","南齐",["齐和帝"],488,502,501,502,3,"明帝子。萧衍所立。502年禅位于萧衍,南齐亡,旋被害。",S_Q),
# ── 梁 502-557 ──
("p_xiao_yan","萧衍","梁武帝","梁",["梁武帝"],464,549,502,549,1,"代齐建梁,在位四十八年,为南朝在位最久者。前期勤政、兴文教、定《梁律》;后崇佛,三度舍身同泰寺。548年纳降将侯景,旋爆发侯景之乱,549年台城陷,饿死于净居殿。",S_L),
("p_xiao_gang","萧纲","梁简文帝","梁",["梁简文帝"],503,551,549,551,3,"武帝子。侯景所立,为傀儡,551年为侯景所弑。工宫体诗。",S_L),
("p_xiao_dong","萧栋","梁豫章王","梁",["豫章王"],None,552,551,552,3,"昭明太子孙。侯景废简文帝立之,旋自代之。侯景败后被杀。",S_L),
("p_xiao_yi","萧绎","梁元帝","梁",["梁元帝"],508,555,552,555,3,"武帝七子。平侯景之乱,即位于江陵。554年西魏破江陵,焚书十四万卷,自谓'读书万卷,犹有今日',旋被杀。",S_L),
("p_xiao_fangzhi","萧方智","梁敬帝","梁",["梁敬帝"],543,558,555,557,3,"元帝子。陈霸先所立。557年禅位于陈霸先,梁亡,旋被害。",S_L),
# ── 陈 557-589 ──
("p_chen_baxian","陈霸先","陈霸先","陈",["陈武帝"],503,559,557,559,2,"代梁建陈。起自寒微,平侯景、拒北齐,收拾江左残局。在位三年而崩。",S_C),
("p_chen_qian","陈蒨","陈文帝","陈",["陈文帝"],522,566,559,566,3,"霸先侄。平王琳、灭留异,复江州湘州,陈政稍固。",S_C),
("p_chen_bozong","陈伯宗","陈废帝","陈",["陈废帝","临海王"],554,570,566,568,3,"文帝子。568年为叔父陈顼所废,旋遇害。",S_C),
("p_chen_xu","陈顼","陈宣帝","陈",["陈宣帝"],530,582,568,582,3,"文帝弟。废侄自立。太建北伐一度收淮南,旋为北周所败,尽失淮南之地。",S_C),
("p_chen_shubao","陈叔宝","陈后主","陈",["陈后主"],553,604,582,589,2,"宣帝子。荒于酒色,作《玉树后庭花》,不理政事。589年隋军入建康,匿于井中被执,陈亡,南北朝终。后卒于洛阳。",S_C),
# ── 北魏 386-534 ──（孝文帝 471-499 已存在）
("p_tuoba_gui","拓跋珪","北魏道武帝","北魏",["北魏道武帝"],371,409,386,409,2,"复代国、改国号魏,定都平城。破后燕据中原,离散诸部、计口授田,奠北魏基业。晚年服寒食散性情暴虐,409年为其子拓跋绍所弑。",S_W),
("p_tuoba_si","拓跋嗣","北魏明元帝","北魏",["北魏明元帝"],392,423,409,423,3,"道武帝子。诛拓跋绍即位。攻取刘宋河南之地。",S_W),
("p_tuoba_tao","拓跋焘","北魏太武帝","北魏",["北魏太武帝"],408,452,423,452,2,"明元帝子。灭夏、北燕、北凉,439年统一北方,结束十六国。太平真君年间灭佛(三武灭佛之首)。452年为宦官宗爱所弑。",S_W),
("p_tuoba_jun","拓跋濬","北魏文成帝","北魏",["北魏文成帝"],440,465,452,465,3,"太武帝孙。即位后复佛法,开凿云冈石窟。",S_W),
("p_tuoba_hong_xianwen","拓跋弘","北魏献文帝","北魏",["北魏献文帝"],454,476,465,471,3,"文成帝子。471年禅位于五岁之子(孝文帝),自为太上皇仍秉政。476年暴崩,史疑为冯太后所鸩。",S_W),
("p_yuan_ke","元恪","北魏宣武帝","北魏",["北魏宣武帝"],483,515,499,515,3,"孝文帝子。承汉化之业,取南朝淮西汉中之地。崇佛,龙门石窟大兴。外戚高肇专权。",S_W),
("p_yuan_xu","元诩","北魏孝明帝","北魏",["北魏孝明帝"],510,528,515,528,3,"宣武帝子,六岁即位,胡太后临朝。六镇起义爆发。528年为胡太后所鸩,旋有河阴之变,尔朱荣尽杀公卿两千余人。",S_W),
("p_yuan_ziyou","元子攸","北魏孝庄帝","北魏",["北魏孝庄帝"],507,531,528,530,3,"尔朱荣所立。河阴之变后受制于尔朱荣,530年伏杀尔朱荣于明光殿,旋为尔朱兆所执缢杀。",S_W),
("p_yuan_gong","元恭","北魏节闵帝","北魏",["北魏节闵帝","前废帝"],498,532,531,532,3,"尔朱世隆所立。高欢起兵破尔朱氏后被废,旋遇害。",S_W),
("p_yuan_xiu","元修","北魏孝武帝","北魏",["北魏孝武帝"],510,535,532,534,3,"高欢所立。不堪高欢挟制,534年西奔宇文泰,北魏遂分东西。旋为宇文泰所鸩。",S_W),
# ── 东魏 534-550 ──
("p_yuan_shanjian","元善见","东魏孝静帝","东魏",["东魏孝静帝"],524,552,534,550,3,"高欢所立,迁都邺。终身为高氏傀儡,叹'自古无不亡之国'。550年禅位于高洋,东魏亡,旋被鸩。",S_W),
# ── 西魏 535-557 ──
("p_yuan_baoju","元宝炬","西魏文帝","西魏",["西魏文帝"],507,551,535,551,3,"宇文泰所立。政出宇文泰,行府兵制、六官之制,关陇集团成形。",S_W),
("p_yuan_qin","元钦","西魏废帝","西魏",["西魏废帝"],525,554,551,554,3,"文帝子。谋除宇文泰事泄被废,旋鸩杀。",S_W),
("p_yuan_kuo","元廓","西魏恭帝","西魏",["西魏恭帝"],537,557,554,557,3,"文帝子。宇文泰所立。557年禅位于宇文觉,西魏亡,旋被害。",S_W),
# ── 北齐 550-577 ──
("p_gao_yang","高洋","北齐文宣帝","北齐",["北齐文宣帝"],526,559,550,559,3,"高欢次子。代东魏建北齐。前期励精图治、破柔然突厥、筑长城;后期酗酒暴虐,滥杀宗室。",S_BQ),
("p_gao_yin","高殷","北齐废帝","北齐",["北齐废帝","济南王"],545,561,559,560,3,"文宣帝子。560年为叔父高演所废,旋遇害。",S_BQ),
("p_gao_yan","高演","北齐孝昭帝","北齐",["北齐孝昭帝"],535,561,560,561,3,"高欢六子。废侄自立。留心政务,颇有治绩,在位一年坠马而崩。",S_BQ),
("p_gao_zhan","高湛","北齐武成帝","北齐",["北齐武成帝"],537,569,561,565,3,"高欢九子。荒淫,杀高殷、高浟等宗室,和士开用事。565年传位其子高纬,自为太上皇。",S_BQ),
("p_gao_wei","高纬","北齐后主","北齐",["北齐后主"],556,577,565,577,3,"武成帝子。宠冯小怜、诛斛律光与兰陵王高长恭,自毁长城。577年北周破邺,北齐亡,与幼主同被诛。",S_BQ),
("p_gao_heng","高恒","北齐幼主","北齐",["北齐幼主"],570,577,577,577,3,"后主子,八岁受禅,在位月余。齐亡被诛。",S_BQ),
# ── 北周 557-581 ──（武帝宇文邕 560-578 已存在）
("p_yuwen_jue","宇文觉","北周孝闵帝","北周",["北周孝闵帝"],542,557,557,557,3,"宇文泰三子。代西魏建北周,称天王。谋除堂兄宇文护事泄,在位九月被废弑。",S_BZ),
("p_yuwen_yu","宇文毓","北周明帝","北周",["北周明帝"],534,560,557,560,3,"宇文泰长子。宇文护所立。有识度,护忌之,560年为护所鸩。",S_BZ),
("p_yuwen_yun","宇文赟","北周宣帝","北周",["北周宣帝"],559,580,578,579,3,"武帝子。武帝崩即纵酒荒淫、诛杀重臣。579年传位幼子自称天元皇帝。580年崩,杨坚遂总揽朝政。",S_BZ),
("p_yuwen_chan","宇文阐","北周静帝","北周",["北周静帝"],573,581,579,581,3,"宣帝子,七岁即位,杨坚辅政。581年禅位于杨坚,北周亡,旋被害。",S_BZ),
]

# ── 护栏:先扫一遍,id 已存在但 name 不符即中止 ──
clash=[]
for row in E:
    id_,name = row[0], row[1]
    p=f"{B}/{id_[2:]}.yaml"
    if os.path.exists(p):
        d=yaml.safe_load(open(p,encoding="utf-8"))
        if isinstance(d,dict) and d.get("name")!=name:
            clash.append((id_, name, d.get("name")))
if clash:
    print("!! id 撞车,已中止,未写入任何文件:")
    for i,exp,act in clash: print(f"   {i}: 期望「{exp}」实为「{act}」")
    sys.exit(1)
print("护栏:无 id 撞车 ✓")

created=updated=0
for row in E:
    id_,name,title,regime,alias,born,died,rs,re_,imp,bio,src = row
    path=f"{B}/{id_[2:]}.yaml"
    if os.path.exists(path):
        d=yaml.safe_load(open(path,encoding="utf-8")); ch=False
        if rs is not None and not d.get("reign_start"): d["reign_start"]=y(rs); ch=True
        if re_ is not None and not d.get("reign_end"): d["reign_end"]=y(re_); ch=True
        roles=d.get("roles") or []
        if "emperor" not in roles: roles.append("emperor"); d["roles"]=roles; ch=True
        ext=d.get("ext") or {}
        if ext.get("title")!=title or ext.get("regime")!=regime:
            ext["title"]=title; ext["regime"]=regime; d["ext"]=ext; ch=True
        if ch: yaml.safe_dump(d,open(path,"w",encoding="utf-8"),allow_unicode=True,sort_keys=False,default_flow_style=False); updated+=1
        continue
    d={"id":id_,"type":"Person","name":name}
    if alias: d["alias"]=alias
    if born is not None: d["born"]=y(born)
    if died is not None: d["died"]=y(died)
    if rs is not None: d["reign_start"]=y(rs)
    if re_ is not None: d["reign_end"]=y(re_)
    d["gender"]="male"; d["roles"]=["emperor"]; d["importance"]=imp; d["bio"]=bio
    d["ext"]={"title":title,"regime":regime}; d["sources"]=src
    yaml.safe_dump(d,open(path,"w",encoding="utf-8"),allow_unicode=True,sort_keys=False,default_flow_style=False); created+=1
print(f"新建 {created}，补字段 {updated}")

CHAINS = {
 "刘宋 420-479": (420,479,["p_liu_yu","p_liu_yifu","p_liu_yilong","p_liu_jun","p_liu_ziye","p_liu_yu_mingdi","p_liu_yu_houfeidi","p_liu_zhun"]),
 "南齐 479-502": (479,502,["p_xiao_daocheng","p_xiao_ze","p_xiao_zhaoye","p_xiao_zhaowen","p_xiao_luan","p_xiao_baojuan","p_xiao_baorong"]),
 "梁 502-557": (502,557,["p_xiao_yan","p_xiao_gang","p_xiao_dong","p_xiao_yi","p_xiao_fangzhi"]),
 "陈 557-589": (557,589,["p_chen_baxian","p_chen_qian","p_chen_bozong","p_chen_xu","p_chen_shubao"]),
 "北魏 386-534": (386,534,["p_tuoba_gui","p_tuoba_si","p_tuoba_tao","p_tuoba_jun","p_tuoba_hong_xianwen","p_tuoba_hong","p_yuan_ke","p_yuan_xu","p_yuan_ziyou","p_yuan_ye","p_yuan_gong","p_yuan_xiu"]),
 "东魏 534-550": (534,550,["p_yuan_shanjian"]),
 "西魏 535-557": (535,557,["p_yuan_baoju","p_yuan_qin","p_yuan_kuo"]),
 "北齐 550-577": (550,577,["p_gao_yang","p_gao_yin","p_gao_yan","p_gao_zhan","p_gao_wei","p_gao_heng"]),
 "北周 557-581": (557,581,["p_yuwen_jue","p_yuwen_yu","p_yuwen_yong","p_yuwen_yun","p_yuwen_chan"]),
}
print("\n=== 在位链连续性自检 ===")
for label,(lo,hi,ids) in CHAINS.items():
    segs=[]
    for i in ids:
        p=f"{B}/{i[2:]}.yaml"
        if not os.path.exists(p): print(f"  [{label}] 缺实体 {i}"); continue
        d=yaml.safe_load(open(p,encoding="utf-8"))
        a=(d.get("reign_start") or {}).get("year"); b=(d.get("reign_end") or {}).get("year")
        if a is None: print(f"  [{label}] {i} 无 reign_start"); continue
        segs.append((a,b if b is not None else a,i))
    segs.sort(); iss=[]
    if segs and segs[0][0]!=lo: iss.append(f"起点 {segs[0][0]}!={lo}")
    if segs and segs[-1][1]!=hi: iss.append(f"讫点 {segs[-1][1]}!={hi}")
    for (a1,b1,i1),(a2,b2,i2) in zip(segs,segs[1:]):
        if b1<a2: iss.append(f"缺口 {b1}~{a2} ({i1}→{i2})")
        elif b1>a2: iss.append(f"重叠 {a2}~{b1} ({i1}×{i2})")
    print(f"  {label}: {len(segs)} 帝 " + ("✓ 链完整" if not iss else "⚠ " + "; ".join(iss)))
