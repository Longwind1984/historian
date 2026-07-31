#!/usr/bin/env python3
"""给 251 条事件/战役定 importance（1 核心 / 2 重要 / 3 一般）。

此前无此字段,时间轴 LOD 只能拿「因果度数 + 描述长度」作代理 —— 等于让 bio 写得长的
事件挤掉写得短的。全景 251 条只显 85 条,选谁全凭这个代理。

判据（见 schema/event.yaml）：
  1 核心：改朝换代、疆域巨变、制度奠基、死伤以百万计者 —— 移走它则该段历史讲不通
  2 重要：影响及于一朝一代者
  3 一般：局部战役、单次事件，或其意义已由所属的更大事件承载者
核心档从严：251 条里只 46 条。凡"某役之一步"（宋灭后蜀/南汉/南唐 等）皆降为 3 ——
其意义已由「宋灭北汉·结束五代十国」承载,不必条条占位。

幂等：已有 importance 即跳过。
"""
import yaml, sys, glob

CORE = {  # 1 核心
    # 上古~先秦：王朝更替与制度奠基
    "b_mingtiao", "b_muye", "e_fengjian_zongfa", "e_gonghe_xingzheng",
    "e_quanrong_po_haojing", "e_pingwang_dongqian", "e_sanjia_fenjin",
    "e_shangyang_bianfa", "b_changping", "e_qin_mie_liuguo",
    # 秦汉
    "e_daze_xiang_qiyi", "e_chuhan_zhanzheng", "e_wang_mang_chuan_han",
    "e_huangjin_qiyi",
    # 魏晋南北朝
    "e_bawang_zhiluan", "e_yongjia_zhiluan", "e_yiguan_nandu", "e_feishui_zhizhan",
    "e_xiaowendi_hanhua",
    # 隋唐
    "e_sui_mie_chen", "e_jian_guo_tang", "e_zhenguan_zhizhi", "e_kaiyuan_shengshi",
    "e_an_lushan_rebellion", "e_huangchao_qiyi", "e_zhuwen_tang",
    # 五代宋辽金元
    "e_shi_jie_liao", "e_yanyun", "e_chenqiao", "e_beijiu_shibingquan",
    "e_chanyuan_zhimeng", "e_jingkang_zhibian", "b_yashan",
    # 明清
    "e_ming_jianli", "e_ming_beifa_dadu", "b_shanhai_guan",
    # 近代
    "e_ya_pian_zhanzheng", "e_taiping_tian_guo", "e_jia_wu_zhanzheng",
    "e_xin_hai_ge_ming", "e_qing_di_tui_wei",
    # 现当代
    "e_qi_qi_shi_bian", "e_prc_founding", "e_da_jihuang",
    "e_wen_hua_da_ge_ming", "e_gaige_kaifang",
}

MINOR = {  # 3 一般：局部战役 / 单次事件 / 意义已由更大事件承载者
    "b_hongshui", "b_chengpu", "b_guiling", "b_maling", "e_wanbi_guizhao",
    "e_jingke_ci_qin", "e_gaixia_zhizhan", "e_baideng_zhi_wei",
    "b_lizhou", "b_boxiang", "b_jiahe", "b_youzhou917", "b_yangcheng",
    "b_nantang_min", "b_nantang_chu", "b_gaoping", "b_liuhe",
    "b_song_jingnan", "b_song_houshu", "b_song_nanhan", "b_song_nantang",
    "b_sanchuankou", "b_haoshuigu", "b_dingchuanzhai",
    "b_huangtiandang", "b_yancheng", "b_ningyuan", "b_yakin",
    "e_wang_xianzhi_qiyi", "e_qingfu_qiyi", "e_pangxun_zhibian",
    "e_huangchao_deng_zhou_jianliang", "e_tian_lingzi_xijian",
    "e_cuiyin_yin_zhuwen", "e_yedu_mutiny", "e_lingren",
    "e_xiantian_zhibian", "e_tanglong_zhengbian", "e_mawei_zhibian",
    "e_duomen_zhibian", "e_gengxu_zhibian", "e_yuanyou_dangbei",
    "e_deng_shishi", "e_zhenli_biaozhun", "e_qingdan",
    "e_shanghai_shibo", "e_beijing_dongao", "e_beijing_aoyun",
    "e_yi_er_ba_shi_bian", "e_ji_nan_can_an", "e_tai_er_zhuang_zhi_zhan",
    "e_qingli_hexi", "e_longxing_beifa", "e_kaixi_beifa",
}

byid = {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("type") in ("Event", "Battle"):
        byid[d["id"]] = (f, d)

# 护栏：手工列举的 id 必须存在(凭记忆猜 id 已翻过车)
missing = [i for i in (CORE | MINOR) if i not in byid]
if missing:
    print("!! 列举的 id 不存在,拒绝执行:", sorted(missing)); sys.exit(1)

n = 0
for eid, (f, d) in byid.items():
    if d.get("importance") is not None:
        continue
    imp = 1 if eid in CORE else 3 if eid in MINOR else 2
    items = list(d.items())
    at = next((i for i, (k, _) in enumerate(items) if k in ("description", "location")), len(items))
    items.insert(at, ("importance", imp))
    yaml.safe_dump(dict(items), open(f, "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False)
    n += 1

import collections
c = collections.Counter(1 if i in CORE else 3 if i in MINOR else 2 for i in byid)
print(f"定档 {n} 条 / 共 {len(byid)}；分布 核心{c[1]} 重要{c[2]} 一般{c[3]}")
