#!/usr/bin/env python3
"""把 Faction.core_members(人名字符串)迁成 member_of/leader_of 关系,并删掉该字段。

问题:core_members 与已存在的 member_of/leader_of 关系(54 条)是同一事实的两套表达 ——
一套是受校验的关系,一套是没人查过的人名字符串。后者的后果:
  1. 123 个名字里 32 个查无此人(上一个脚本已补建),库自己不知道;
  2. EntityDetail.vue 把人名当 id 渲染成可点链接 —— 理学派详情里点「周敦颐」是死链。

正解是关系归 relations。本脚本:
  - 人名 → Person id(含 alias 命中:徐知诰=李昪、章炳麟=章太炎;剥「朱温(降唐前)」的括号注释)
  - 已有等价关系者跳过(44 条),只补缺的
  - 该 Faction 尚无领袖登记、且此人正是其首脑者 → leader_of,余为 member_of
  - 删除 core_members 字段(数据 + schema)

不写 since/until —— 成员起讫年多不可考,编不如缺。既有关系带 since/until 的保持不动。
"""
import yaml, glob, pathlib, sys, collections

OUT = "data/relations/faction_members.yaml"

# 该 Faction 尚无 leader_of/founded 登记,且此人是其首脑
LEADERS = {
    ("f_donglin_dang",    "p_guxiancheng"),   # 修复东林书院讲学,「东林党」之名由是起
    ("f_jingnan_ji",      "p_yongle"),        # 靖难之役的发动者
    ("f_khitan",          "p_yeluabaoji"),    # 契丹开国
    ("f_nantang_faction", "p_songqiqiu"),     # 南唐党争的党魁
    ("f_yangwu_group",    "p_yanghangmi"),    # 杨吴奠基者
}

# 逐条 note:说清此人在这个集团里是什么位置,沿用库中既有风格(如「义社十兄弟之一」)
NOTE = {
  ("f_daoxue_pai","p_chenghao"): "与弟程颐并称二程,洛学奠基",
  ("f_donglin_dang","p_guxiancheng"): "1594 削籍归里,修复东林书院讲学,东林之名由是起",
  ("f_donglin_dang","p_yanglian"): "劾魏忠贤二十四大罪,死于诏狱",
  ("f_donglin_dang","p_cbdb_127031"): "东林六君子之一,与杨涟同死诏狱",
  ("f_donglin_dang","p_gaopanlong"): "与顾宪成并称顾高,1626 阉党缉捕时投池死",
  ("f_eunuch_tang","p_tianlingzi"): "僖宗朝神策军中尉,僖宗呼为阿父",
  ("f_eunuch_tang","p_yangfugong"): "昭宗朝神策军中尉,养子分据藩镇号外宅郎君",
  ("f_eunuch_tang","p_juwenzhen"): "805 逼顺宗内禅,宦官废立之权自此始",
  ("f_eunuch_tang","p_wangshoucheng"): "历宪穆敬文四朝,穆宗文宗皆其所立",
  ("f_eunuch_tang","p_yu_chao_en"): "代宗朝观军容使,领神策军",
  ("f_guanlong","p_libi"): "八柱国之一",
  ("f_heshuo","p_wang_wujun"): "成德节度使",
  ("f_heshuo","p_tian_yue"): "魏博节度使,四镇称王之一",
  ("f_heshuo","p_luoshaowei"): "魏博节度使,907 借朱温兵尽诛牙军",
  ("f_huaijun_bei_yang","p_duan_qirui"): "北洋之虎,皖系首领",
  ("f_huaijun_bei_yang","p_feng_guozhang"): "直系首领",
  ("f_huaixi_ji","p_lishanchang"): "明开国首相,淮西集团文首",
  ("f_huaixi_ji","p_xuda"): "明开国第一功臣,魏国公",
  ("f_huaixi_ji","p_changyuchun"): "常胜先锋,开平王",
  ("f_huaixi_ji","p_tanghe"): "与朱元璋同里,最早招其入伍者;洪武功臣中独得善终",
  ("f_huaixi_ji","p_lanyu"): "捕鱼儿海破北元,后族诛于蓝玉案",
  ("f_huangchao_army","p_mengkai"): "巢部尚书左仆射,883 战死于陈州",
  ("f_jingnan_ji","p_yongle"): "靖难之役发动者,即位为明成祖",
  ("f_jingnan_ji","p_yaoguangxiao"): "黑衣宰相,劝棣起兵",
  ("f_jingnan_ji","p_zhangyu_ming"): "靖难第一名将,东昌之战为救朱棣战死",
  ("f_jingnan_ji","p_zhuneng"): "张玉死后独当大任,封成国公",
  ("f_khitan","p_yeluabaoji"): "契丹开国,辽太祖",
  ("f_khitan","p_yeludeguang"): "辽太宗,946 灭后晋",
  ("f_khitan","p_shulüping"): "太祖皇后,断腕留冢,废长立次",
  ("f_li_dang","p_zhengtan"): "李党要角,精经学,尝请废进士科",
  ("f_literati_5d","p_heningwd"): "曲子相公,历五朝,撰疑狱集",
  ("f_literati_5d","p_lisong_wd"): "后晋宰相,948 为苏逢吉诬杀",
  ("f_nantang_faction","p_songqiqiu"): "南唐开国谋主,党争魁首",
  ("f_nantang_faction","p_fengyansi"): "宋齐丘党,词冠五代",
  ("f_nantang_faction","p_sunsheng"): "使后周不屈见杀",
  ("f_nantang_faction","p_hanxizai"): "知国将亡不欲当其咎,纵情声色自污",
  ("f_niu_dang","p_cbdb_32980"): "牛党要角",
  ("f_niu_dang","p_cbdb_32225"): "牛党要角,宣宗朝宰相",
  ("f_qian_group","p_qianyuanguan"): "吴越二世",
  ("f_qian_group","p_qianhongchu"): "吴越末主,978 纳土归宋",
  ("f_shatuo","p_guowei"): "后周太祖,出于沙陀系",
  ("f_shatuo","p_chairong"): "后周世宗",
  ("f_shatuo","p_liuchong"): "北汉开国,后汉宗室",
  ("f_taiping","p_yangxiuqing"): "东王,1856 天京事变中被杀",
  ("f_taiping","p_shidakai"): "翼王,天京事变后出走",
  ("f_taiping","p_weichanghui"): "北王,1856 奉密诏诛杨秀清,屠其部属两万余人,旋被诛",
  ("f_tongmenghui","p_huang_xing"): "同盟会执行部庶务,与孙中山并称孙黄",
  ("f_tongmenghui","p_song_jiaoren"): "同盟会司法部检事长,民初组国民党",
  ("f_tongmenghui","p_zhang_taiyan"): "民报总编辑",
  ("f_xiangjun","p_zuozongtang"): "楚军统帅,后收复新疆",
  ("f_xiangjun","p_hulinyi"): "湖北巡抚,湘军后勤与财政中枢",
  ("f_xiangjun","p_pengyulin"): "湘军水师创建者",
  ("f_xin_jiu_dang","p_lvhuiqing"): "新党,王安石之副,后与安石反目",
  ("f_xin_jiu_dang","p_zhangdun"): "新党,绍圣绍述的主持者",
  ("f_yandang","p_cuichengxiu"): "阉党五虎之首,魏忠贤谋主",
  ("f_yangwu_group","p_yanghangmi"): "杨吴奠基者,淮南节度使",
  ("f_yangwu_group","p_xuwen"): "杨吴权臣,专吴政二十年",
  ("f_yangwu_group","p_li_bian"): "徐温养子,937 代吴建南唐",
  ("f_yishe_shixiongdi","p_wangshenqi"): "义社十兄弟之一,陈桥兵变为内应",
  ("f_yishe_shixiongdi","p_lijixun"): "义社十兄弟之一,年最长",
  ("f_yishe_shixiongdi","p_hanzhongyun"): "义社十兄弟之一,陈桥兵变为控鹤军都指挥使",
  ("f_yuanyou_dangren","p_suzhe"): "元祐党人,苏轼之弟",
  ("f_yuanyou_dangren","p_huangtingjian"): "苏门四学士,名列元祐党人碑",
  ("f_yuanyou_dangren","p_chengyi"): "元祐党人,洛学领袖",
  ("f_zhuwen_group","p_zhuyouzhen"): "朱温之子,后梁末帝",
  ("f_zhuwen_group","p_jingxiang"): "朱温谋主,后梁亡时自杀",
  ("f_zhuwen_group","p_zhangquanyi"): "河南尹,为朱温经营洛阳",
  ("f_zhuwen_group","p_gecongzhou"): "朱温麾下第一名将,山东一条葛",
  ("f_zhuzhan_touxiang","p_hanshizhong"): "主战派,黄天荡阻兀术",
  ("f_zhuzhan_touxiang","p_zhangjun_song"): "主战派领袖,两度当国两度丧师",
  ("f_zhuzhan_touxiang","p_jiasidao"): "南宋末权相,主和,鲁港之溃",
}

# ── 解析 ────────────────────────────────────────────────────────────────
files, ents = {}, {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"): ents[d["id"]] = d; files[d["id"]] = f

byname = {}
for d in ents.values():
    if d.get("type") != "Person": continue
    for n in [d.get("name")] + list(d.get("alias") or []):
        if n: byname.setdefault(n, []).append(d["id"])

def resolve(m):
    key = m.split("(")[0].split("（")[0].strip()   # 「朱温(降唐前)」→「朱温」
    ids = byname.get(key, [])
    seed = [i for i in ids if not i.startswith("p_cbdb_")]
    pick = seed or ids
    return pick[0] if len(pick) == 1 else None

have = collections.defaultdict(dict)
for f in glob.glob("data/relations/*.yaml"):
    for r in (yaml.safe_load(open(f, encoding="utf-8")) or []):
        if isinstance(r, dict) and r.get("type") in ("member_of","leader_of","founded") \
           and str(r.get("to","")).startswith("f_"):
            have[r["to"]][r["from"]] = r["type"]

new, seen, unresolved = [], set(), []
for f in sorted(glob.glob("data/entities/factions/*.yaml")):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    fid = d["id"]
    for m in (d.get("core_members") or []):
        pid = resolve(m)
        if pid is None: unresolved.append(f"{fid}:{m}"); continue
        if pid in have[fid] or (fid, pid) in seen: continue   # 已有等价关系 / 同人重复列名
        seen.add((fid, pid))
        note = NOTE.get((fid, pid))
        if not note: unresolved.append(f"{fid}:{m}({pid}) 缺 note"); continue
        new.append({"from": pid, "to": fid,
                    "type": "leader_of" if (fid, pid) in LEADERS else "member_of",
                    "note": note})

if unresolved:
    sys.exit("✗ 未处理项,拒绝迁移(先补齐再跑):\n  " + "\n  ".join(unresolved))

pathlib.Path(OUT).write_text(
    "# 由 Faction.core_members 迁移而来(2026-07-16)。原字段存的是人名字符串,不受校验、\n"
    "# 且被 EntityDetail 当 id 渲染成死链。关系归 relations,故删字段留关系。\n"
    "# 成员起讫年多不可考,故不写 since/until —— 编不如缺。\n"
    + yaml.safe_dump(new, allow_unicode=True, sort_keys=False, default_flow_style=False, width=200),
    encoding="utf-8")

# 删字段
n = 0
for f in glob.glob("data/entities/factions/*.yaml"):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if "core_members" in d:
        d.pop("core_members")
        yaml.safe_dump(d, open(f, "w", encoding="utf-8"), allow_unicode=True,
                       sort_keys=False, default_flow_style=False, width=200)
        n += 1
print(f"新建 {len(new)} 条关系 → {OUT};从 {n} 个 Faction 删除 core_members 字段")
