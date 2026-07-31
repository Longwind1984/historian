#!/usr/bin/env python3
"""合并 2 组 Event/Battle 双重建模:崖山海战、土木堡之变。

这两件事各被建模两遍(一份 Battle 一份 Event),在时间轴上并排显示为两张卡。
分类可视化上线后二者甚至互相矛盾:崖山海战(南宋亡)印「戰」而 崖山海战 印「滅」。

留 Battle 弃 Event:Battle 有 combatants/commanders/victor 这些战役专属字段,
Event 那份只是其真子集(各多一条独有信息,已嫁接过去)。

顺带修 id 约定:Battle「土木堡之变」的 id 是 e_tumubao(Battle 用了 e_ 前缀),
其零引用,可安全改名 b_tumubao。

幂等:目标不存在即跳过。
"""
import re, sys, glob, pathlib

REPO = pathlib.Path(".")

# ── 1. 嫁接 Event 独有信息到保留的 Battle ──
GRAFT = [
    # (Battle 文件, 原文, 新文) —— Event 里唯一比 Battle 多的细节
    ("data/entities/battles/yashan.yaml",
     "宋军千余艘战船连成水寨。决战宋军全军覆没。",
     "宋军千余艘战船连成水寨,被围断水二十余日。决战宋军全军覆没。"),
    # Event 那份带配图,Battle 没有 → 补到末尾
    ("data/entities/battles/tumubao.yaml",
     "sources:\n- 明史·英宗本纪\n",
     "sources:\n- 明史·英宗本纪\nimage: https://commons.wikimedia.org/wiki/Special:FilePath/Tumu Crisis.jpg\n"),
]

# ── 2. id 重指:被删 Event 的引用 → 保留的 Battle;另修 Battle 的 e_ 前缀 ──
RENAME = {
    "e_yashan_zhibian": "b_yashan",
    "e_tumubian": "b_tumubao",
    "e_tumubao": "b_tumubao",   # id 约定:Battle 应为 b_ 前缀(零引用,安全)
}

# ── 3. 删除的重复 Event ──
DELETE = ["data/entities/events/yashan_zhibian.yaml",
          "data/entities/events/tumubian.yaml"]

n_graft = n_ref = n_del = 0

for path, old, new in GRAFT:
    p = REPO / path
    if not p.exists():
        continue
    s = p.read_text(encoding="utf-8")
    if new in s:            # 已嫁接
        continue
    if old not in s:
        print(f"!! 嫁接锚点未命中,跳过: {path}"); sys.exit(1)
    p.write_text(s.replace(old, new, 1), encoding="utf-8")
    n_graft += 1

# 先删,再重指(避免把待删文件里的自身 id 也改了)
for path in DELETE:
    p = REPO / path
    if p.exists():
        p.unlink(); n_del += 1

# 词边界替换:防止 pl_yashan2 之类被误伤;e_tumubao 与 e_tumubian 互不为子串但仍用边界
targets = glob.glob("data/relations/*.yaml") + glob.glob("data/entities/**/*.yaml", recursive=True)
for f in targets:
    p = pathlib.Path(f)
    s = old_s = p.read_text(encoding="utf-8")
    for src, dst in RENAME.items():
        s = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(src)}(?![A-Za-z0-9_])", dst, s)
    if s != old_s:
        p.write_text(s, encoding="utf-8"); n_ref += 1

print(f"嫁接 {n_graft} 处 / 重指 {n_ref} 个文件 / 删除 {n_del} 个重复 Event")
