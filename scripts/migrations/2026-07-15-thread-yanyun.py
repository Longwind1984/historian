#!/usr/bin/env python3
"""给事件打「线索」标签(ext.threads),先落第一条:燕云十六州。

为什么不用 led_to:
  Rick 要的是「割让与收复」相连(936 石敬瑭割 → 1368 徐达克大都复)。但这两件事
  之间没有因果——明北伐终结了燕云问题,并非被割让所「导致」。硬连一条跨 432 年的
  led_to 是史学家不会做的因果陈述,与「求真」相悖。
  因果(led_to)回答「谁引发了谁」,线索(thread)回答「哪些事同属一个历史问题」。
  二者正交:燕云线索里 澶渊之盟→海上之盟 有因果,而 割燕云↔明北伐 只有主题同一。

线索成员按「燕云的得与失」这一问题串起,不预设立场:
  936 割让 → 三次武力收复(959/979/986) → 澶渊放弃武力 → 联金复燕反致亡国 → 1368 复归

幂等:已在 threads 里就跳过。
"""
import yaml, sys, glob, pathlib

THREAD = "燕云十六州"
MEMBERS = [
    ("e_shi_jie_liao",     "石敬瑭乞契丹之师,割地为酬——燕云之失由此"),
    ("e_yanyun",           "十六州入契丹,中原失长城之险"),
    ("b_houzhou_liao",     "周世宗亲征,取三关三州而崩,复燕之始"),
    ("b_gaolianghe",       "宋太宗径攻幽州,高梁河大败"),
    ("b_yongxi_beifa",     "三路再伐,岐沟关溃、杨业殁,武力收复之志绝"),
    ("e_chanyuan_zhimeng", "以岁币易和,燕云之失就此定局"),
    ("e_haishang_zhimeng", "约金夹攻辽以复燕云"),
    ("e_jingkang_zhibian", "复燕未几,金反南下,北宋亡——收复之图适成亡国之由"),
    ("e_ming_beifa_dadu",  "徐达克大都,燕云复归,距石敬瑭割让四百三十二年"),
]

# id -> 文件(按 id 查,不按文件名猜——踩过 e_zhou_reform/e_zhoushizong_gaige 的坑)
byid = {}
for f in glob.glob("data/entities/**/*.yaml", recursive=True):
    d = yaml.safe_load(open(f, encoding="utf-8"))
    if isinstance(d, dict) and d.get("id"):
        byid[d["id"]] = f

missing = [i for i, _ in MEMBERS if i not in byid]
if missing:
    print("!! 线索成员 id 不存在,拒绝执行:", missing)
    sys.exit(1)

n = 0
for eid, why in MEMBERS:
    f = byid[eid]
    d = yaml.safe_load(open(f, encoding="utf-8"))
    ext = d.setdefault("ext", {})
    threads = ext.setdefault("threads", [])
    if any(t.get("name") == THREAD for t in threads):
        continue
    threads.append({"name": THREAD, "role": why})
    yaml.safe_dump(d, open(f, "w", encoding="utf-8"), allow_unicode=True,
                   sort_keys=False, default_flow_style=False)
    n += 1

print(f"「{THREAD}」线索:{n} 条打标(共 {len(MEMBERS)} 个成员)")
