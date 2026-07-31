#!/usr/bin/env python3
"""全量事件重扫归 5族17类。Claude 逐条判定(198 条)。
原 coup/institution 被当垃圾桶:战役/民变/战争/党争/工程 全塞在里面。"""
import yaml, glob

# 事件名 -> 新 category（仅列需要改的；未列出者保持原样）
M = {
 # ── 民变·起义:原全被塞进 institution/coup ──
 "大泽乡起义":"rebellion", "绿林赤眉起义":"rebellion", "黄巾起义":"rebellion",
 "六镇之乱":"rebellion", "侯景之乱":"rebellion", "隋末农民起义":"rebellion",
 "安史之乱":"rebellion", "裘甫起义":"rebellion", "庞勋之变":"rebellion",
 "黄巢起义":"rebellion", "王仙芝起义":"rebellion", "黄巢攻入长安":"rebellion",
 "红巾军起义":"rebellion", "太平天国运动":"rebellion", "义和团运动":"rebellion",
 "七国之乱":"rebellion", "辛亥革命":"rebellion", "二次革命":"rebellion", "护国运动":"rebellion",
 # ── 战争(跨年多役):原塞在 institution/coup/battle ──
 "楚汉战争":"war", "诸葛亮北伐":"war", "八王之乱":"war", "永嘉之乱":"war",
 "隋征高句丽":"war", "唐收复两京":"war", "沙陀助唐平黄巢":"war",
 "隆兴北伐(符离之溃)":"war", "开禧北伐":"war", "靖难之役":"war", "庚戌之变":"war",
 "平定三藩":"war", "十全武功":"war", "第一次鸦片战争":"war", "甲午中日战争":"war",
 "北伐战争":"war", "九一八事变":"war", "一二八事变":"war", "七七事变":"war",
 "长征":"war", "三大战役":"war",
 # ── 战役(单次) ──
 "土木堡之变":"battle", "台儿庄战役":"battle", "崖山海战(南宋亡)":"battle",
 # ── 灭国·分合 ──
 "北魏分裂":"conquest", "北周灭北齐":"conquest", "隋灭陈统一":"conquest",
 "唐灭东突厥":"conquest", "回鹘汗国灭亡":"conquest", "石敬瑭借契丹灭后唐":"conquest",
 "靖康之变":"conquest", "联蒙灭金":"conquest", "秦灭六国":"conquest",
 # ── 党争·清洗:原塞在 institution/coup ──
 "焚书坑儒":"purge", "巫蛊之祸":"purge", "党锢之祸":"purge", "河阴之变":"purge",
 "牛李党争":"purge", "白马驿之祸":"purge", "元祐党争":"purge", "元祐党人碑":"purge",
 "大礼议":"purge", "四一二事件":"purge",
 # ── 继统·禅代 ──
 "王莽篡汉":"succession", "杨坚代周":"succession", "武周革命":"succession",
 # ── 开国·立政(新类) ──
 "唐朝建立":"founding", "郭威建后周":"founding", "契丹建国":"founding",
 "中国共产党成立":"founding", "中华人民共和国成立":"founding",
 # ── 科技·工程(新类) ──
 "大禹治水":"science", "大运河开通":"science", "第一颗原子弹爆炸":"science",
 "第一颗氢弹爆炸":"science", "东方红一号卫星":"science", "神舟五号载人航天":"science",
 "三峡工程":"science",
 # ── 疆土·迁徙 ──
 "盘庚迁殷":"territory", "衣冠南渡":"territory", "张义潮归唐(归义军)":"territory",
 "吴越纳土归宋":"territory", "建炎南渡":"territory", "收复台湾":"territory",
 "香港回归":"territory", "澳门回归":"territory",
 "割燕云十六州":"territory",   # 原 treaty;其实质是疆土割让,与"收复"同族方成线索
 # ── 盟约·条约 ──
 "海上之盟":"treaty",
 # ── 文化·盛会 ──
 "白虎观会议":"culture", "北京奥运会":"culture", "上海世博会":"culture", "北京冬奥会":"culture",
}

n=0; miss=[]
seen=set()
for f in glob.glob("data/entities/events/*.yaml"):
    d=yaml.safe_load(open(f,encoding="utf-8"))
    if not isinstance(d,dict): continue
    nm=d.get("name")
    if nm in M:
        seen.add(nm)
        if d.get("category")!=M[nm]:
            old=d["category"]; d["category"]=M[nm]
            yaml.safe_dump(d,open(f,"w",encoding="utf-8"),allow_unicode=True,sort_keys=False,default_flow_style=False)
            n+=1
miss=[k for k in M if k not in seen]
print(f"重扫改类 {n} 条")
if miss: print("!! 映射中未匹配到实体(名字对不上):", miss)
