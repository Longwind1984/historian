#!/usr/bin/env python3
"""统一帝王称谓:ext.title=大众通称(帝王带标签), ext.regime=政权(着色/割据表达)。
规则:帝号(庙号/谥号) > 年号(明清) > 本名;一律以大众实际通称为准。"""
import yaml, glob, os
B = "/Users/rick/ZCodeProject/history-kb/.claude/worktrees/project-version-roadmap-872b4e/data/entities/persons"

M = {
 # 先秦
 "p_dayu":("禹","夏"), "p_qi_xia":("启","夏"), "p_jie_xia":("夏桀","夏"),
 "p_shangtang":("商汤","商"), "p_pangeng":("盘庚","商"), "p_wuding":("武丁","商"), "p_di_xin":("商纣王","商"),
 "p_zhou_wu_wang":("周武王","西周"), "p_zhou_cheng_wang":("周成王","西周"), "p_zhou_li_wang":("周厉王","西周"),
 "p_zhou_xuan_wang":("周宣王","西周"), "p_zhou_you_wang":("周幽王","西周"), "p_zhou_ping_wang":("周平王","东周"),
 "p_ying_zheng":("秦始皇","秦"), "p_zi_ying":("子婴","秦"),
 # 西汉
 "p_liu_bang_qin":("汉高祖","西汉"), "p_liu_ying":("汉惠帝","西汉"), "p_liu_gong":("前少帝","西汉"),
 "p_liu_hong_shaodi":("后少帝","西汉"), "p_liu_heng":("汉文帝","西汉"), "p_liu_qi":("汉景帝","西汉"),
 "p_liu_che":("汉武帝","西汉"), "p_liu_fuling":("汉昭帝","西汉"), "p_liu_he_changyi":("刘贺","西汉"),
 "p_liu_xun":("汉宣帝","西汉"), "p_liu_shi":("汉元帝","西汉"), "p_liu_ao":("汉成帝","西汉"),
 "p_liu_xin_aidi":("汉哀帝","西汉"), "p_liu_kan":("汉平帝","西汉"), "p_ruzi_ying":("孺子婴","西汉"),
 "p_wang_mang":("王莽","新"),
 # 东汉
 "p_liu_xiu":("汉光武帝","东汉"), "p_liu_zhuang":("汉明帝","东汉"), "p_liu_da":("汉章帝","东汉"),
 "p_liu_zhao":("汉和帝","东汉"), "p_liu_long":("汉殇帝","东汉"), "p_liu_hu":("汉安帝","东汉"),
 "p_liu_yi_shaodi":("汉前少帝","东汉"), "p_liu_bao":("汉顺帝","东汉"), "p_liu_bing":("汉冲帝","东汉"),
 "p_liu_zuan":("汉质帝","东汉"), "p_liu_zhi_huandi":("汉桓帝","东汉"), "p_liu_hong_lingdi":("汉灵帝","东汉"),
 "p_liu_bian":("汉少帝","东汉"), "p_liu_xie":("汉献帝","东汉"),
 # 三国(本名为通称)
 "p_cao_cao":("曹操","曹魏"), "p_cao_pi":("曹丕","曹魏"), "p_liu_bei":("刘备","蜀汉"), "p_sun_quan":("孙权","东吴"),
 # 两晋 / 十六国
 "p_sima_yan_wudi":("晋武帝","西晋"), "p_sima_zhong":("晋惠帝","西晋"), "p_sima_chi":("晋怀帝","西晋"), "p_sima_ye":("晋愍帝","西晋"),
 "p_sima_rui":("晋元帝","东晋"), "p_sima_shao":("晋明帝","东晋"), "p_sima_yan_chengdi":("晋成帝","东晋"),
 "p_sima_yue_kangdi":("晋康帝","东晋"), "p_sima_dan":("晋穆帝","东晋"), "p_sima_pi":("晋哀帝","东晋"),
 "p_sima_yi_feidi":("晋废帝","东晋"), "p_sima_yu":("晋简文帝","东晋"), "p_sima_yao":("晋孝武帝","东晋"),
 "p_sima_dezong":("晋安帝","东晋"), "p_sima_dewen":("晋恭帝","东晋"),
 "p_fu_jian":("苻坚","前秦"),
 # 南北朝
 "p_liu_yu":("刘裕","刘宋"), "p_tuoba_hong":("北魏孝文帝","北魏"), "p_yuwen_yong":("北周武帝","北周"),
 # 隋唐
 "p_yangjian":("隋文帝","隋"), "p_yangguang":("隋炀帝","隋"),
 "p_liyuan":("唐高祖","唐"), "p_li_shimin":("唐太宗","唐"), "p_li_zhi":("唐高宗","唐"),
 "p_li_dan":("唐睿宗","唐"), "p_wu_zetian":("武则天","武周"), "p_li_xian_zhongzong":("唐中宗","唐"),
 "p_li_longji":("唐玄宗","唐"), "p_li_heng_suzong":("唐肃宗","唐"), "p_li_yu_daizong":("唐代宗","唐"),
 "p_li_kuo":("唐德宗","唐"), "p_li_song":("唐顺宗","唐"), "p_li_chun":("唐宪宗","唐"),
 "p_li_heng_muzong":("唐穆宗","唐"), "p_li_zhan":("唐敬宗","唐"), "p_li_ang":("唐文宗","唐"),
 "p_li_yan_wuzong":("唐武宗","唐"), "p_li_chen":("唐宣宗","唐"), "p_li_cui":("唐懿宗","唐"),
 "p_li_xuan_xizong":("唐僖宗","唐"), "p_li_ye":("唐昭宗","唐"), "p_li_zhu":("唐哀帝","唐"),
 # 五代十国
 "p_zhuwen":("朱温","后梁"), "p_shijingtan":("石敬瑭","后晋"), "p_chairong":("柴荣","后周"), "p_liyu":("李煜","南唐"),
 # 辽金西夏
 "p_yeluabaoji":("辽太祖","辽"), "p_liyuanhao":("李元昊","西夏"), "p_wanyanaguda":("完颜阿骨打","金"),
 # 两宋
 "p_zhaokuangyin":("宋太祖","北宋"), "p_zhaoguangyi":("宋太宗","北宋"), "p_renzong":("宋仁宗","北宋"),
 "p_huizong":("宋徽宗","北宋"), "p_gaozong":("宋高宗","南宋"),
 # 蒙元
 "p_chengjisihan":("成吉思汗","蒙古"), "p_hubilai":("忽必烈","元"),
 # 明(本名/年号为通称)
 "p_zhuyuanzhang":("朱元璋","明"), "p_yongle":("朱棣","明"), "p_jiajing":("嘉靖帝","明"),
 "p_wanli":("万历帝","明"), "p_chongzhen":("崇祯帝","明"),
 # 清
 "p_nuerhaci":("努尔哈赤","后金"), "p_huangtaiji":("皇太极","清"), "p_kangxi":("康熙帝","清"),
 "p_yongzheng":("雍正帝","清"), "p_qianlong":("乾隆帝","清"), "p_xuantong":("溥仪","清"),
 # 民国
 "p_yuanshikai":("袁世凯","中华帝国"),
}

done=0; miss=[]
for f in glob.glob(B+"/*.yaml"):
    d=yaml.safe_load(open(f,encoding="utf-8"))
    if not isinstance(d,dict) or "emperor" not in (d.get("roles") or []): continue
    i=d.get("id")
    if i not in M: miss.append((i, d.get("name"))); continue
    t,r = M[i]
    ext=d.get("ext") or {}
    ext["title"]=t; ext["regime"]=r
    d["ext"]=ext
    yaml.safe_dump(d, open(f,"w",encoding="utf-8"), allow_unicode=True, sort_keys=False, default_flow_style=False)
    done+=1
print(f"已设 ext.title/ext.regime: {done} 帝")
if miss: print("未覆盖(将回退 alias[0]/name):", miss)
