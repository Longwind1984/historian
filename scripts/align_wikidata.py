#!/usr/bin/env python3
"""把本库人物对齐到 Wikidata,一次取回三样东西:QID / P18 图像 / 中文维基条目名。

为什么合成一个脚本:这三样出自同一条 SPARQL 的同一行结果。拆成两次跑等于把
WDQS 的限流(匿名约 1 次/分钟,重查询更狠)白挨两遍。

为什么需要它:全库 102 个 image 字段是早期脚本按「中文名 -> Commons 文件名」硬编码
猜出来的,未经核对。实测抽查李白/杜甫皆 404,整体失效率约 78% —— 也就是说站上大多数
头像位现在是空的。本脚本不猜:只认 Wikidata 上明确挂着的 P18。

两级匹配,置信度递降:
  L1  CBDB ID -> P497。确定性,零猜测。data/cbdb_seed_map.yaml 有 369 条。
      坑:Wikidata 的 P497 格式约束是 7 位数字,而 CBDB 原始 id 变长 —— VALUES 里
      必须同时写裸数字与零填充两种形式,只写一种会漏掉一半。
  L2  中文名 + 生卒年消歧。rdfs:label/skos:altLabel 命中且 P569/P570 与我方
      born/died 相差 <= TOL 年才接受。同名跨朝代者(如多个「王安」)靠这一条挡住。
  其余留空。docs/content-spec.md §7「无出处不硬补」—— 低置信匹配一律不写,
  让 SVG 占位兜住,不猜。

明确不做:4892 个 p_cbdb_* 批量导入人物不找图。实测 Wikidata 上带 P497 的 41.3 万条
里只有 2381 条带 P18(0.58%),在他们身上花的请求几乎全部落空。他们仍可取 QID 做外链。

产出(都不直接改 data/,给人先看):
  <out>/wikidata_align.jsonl   逐条结果,断点续跑的依据
  <out>/wikidata_align.csv     对账表,供抽样人工复核
写回 YAML 是另一步(--apply),读的就是上面这份 jsonl。

用法:
  uv run --with pyyaml python3 scripts/align_wikidata.py --stage query   # 跑 SPARQL
  uv run --with pyyaml python3 scripts/align_wikidata.py --stage verify  # 复检图 URL + 取许可
  uv run --with pyyaml python3 scripts/align_wikidata.py --stage report  # 出 CSV
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import ssl
import sys
import time
import urllib.parse
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
PERSONS = ROOT / "data" / "entities" / "persons"
CBDB_MAP = ROOT / "data" / "cbdb_seed_map.yaml"

WDQS = "https://query.wikidata.org/sparql"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# WDQS 明确要求可识别的 UA,匿名默认 UA 会被更早限流
UA = "history-kb-align/1.0 (https://github.com/; contact via repo) python-urllib"

TOL = 3          # 生卒年容差(年)。史料系年常差一两年,差 3 年以上视为不同人
BATCH = 250      # 单次 VALUES 条数。369 条一次性 GET 会 414,故一律 POST
SLEEP = 8.0      # 批间隔。WDQS 匿名限流,宁慢勿被封
TIMEOUT = 60     # 单请求超时。外部调用必须有超时上限,否则一次挂起 = 整脚本永久卡死

_CTX = ssl.create_default_context()


def _post(url: str, data: dict, accept: str) -> str:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": UA, "Accept": accept,
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_CTX) as r:
        return r.read().decode("utf-8", "replace")


def sparql(query: str, tries: int = 3) -> list[dict]:
    """跑一条 SPARQL。失败重试带退避;连续失败就放弃这一批并往上抛 ——
    宁可这批标记未决、留待下次续跑,也不要卡在原地重试到天荒地老。"""
    for i in range(tries):
        try:
            txt = _post(WDQS, {"query": query, "format": "json"}, "application/sparql-results+json")
            return json.loads(txt)["results"]["bindings"]
        except Exception as e:  # noqa: BLE001
            wait = SLEEP * (2 ** i)
            print(f"    ! SPARQL 失败({e.__class__.__name__}: {e}),{wait:.0f}s 后重试 {i+1}/{tries}",
                  file=sys.stderr)
            if i == tries - 1:
                raise
            time.sleep(wait)
    return []


# ---------------------------------------------------------------- 载入本库人物

def load_people() -> list[dict]:
    """只取种子人物(非 p_cbdb_*)。CBDB 批量导入的 4892 人图覆盖率 0.58%,不值当。"""
    cbdb = yaml.safe_load(CBDB_MAP.read_text(encoding="utf-8")) or {}
    out = []
    for f in sorted(PERSONS.glob("*.yaml")):
        if f.stem.startswith("cbdb_"):
            continue
        d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if not d.get("id") or d.get("id", "").startswith("p_cbdb_"):
            continue
        out.append({
            "id": d["id"],
            "file": f.name,
            "name": d.get("name"),
            "born": (d.get("born") or {}).get("year"),
            "died": (d.get("died") or {}).get("year"),
            "importance": d.get("importance"),
            # cbdb_seed_map 的键是文件名 stem 而不是实体 id(bai_juyi vs p_bai_juyi)
            "cbdb": cbdb.get(f.stem),
            "has_image": bool(d.get("image")),
        })
    return out


# ---------------------------------------------------------------- L1 / L2 查询

def q_by_cbdb(rows: list[dict]) -> str:
    vals = []
    for r in rows:
        c = str(r["cbdb"])
        # 双写:Wikidata P497 约束 7 位,我们的 id 变长。只写一种会漏。
        vals.append(f'"{c}"')
        if len(c) < 7:
            vals.append(f'"{c.zfill(7)}"')
    return f"""
SELECT ?cbdb ?item ?img ?zh WHERE {{
  VALUES ?cbdb {{ {' '.join(sorted(set(vals)))} }}
  ?item wdt:P497 ?cbdb .
  OPTIONAL {{ ?item wdt:P18 ?img }}
  OPTIONAL {{ ?zhArt schema:about ?item ; schema:isPartOf <https://zh.wikipedia.org/> ;
                     schema:name ?zh }}
}}"""


def q_by_label(rows: list[dict]) -> str:
    """标签必须写成带语言标签的字面量("李白"@zh),不能用 FILTER(STR(?x)=...)。
    前者直接命中标签索引;后者要求先扫出所有 zh 标签再逐条比字符串 —— 实测
    这么写 60s 超时,改成 @zh 字面量后秒回。简繁两种字形都列上,库里两种都有。"""
    names = sorted({r["name"] for r in rows if r.get("name")})
    vals = " ".join(f'"{n}"@{tag}' for n in names for tag in ("zh", "zh-hans", "zh-hant"))
    return f"""
SELECT ?lab ?item ?img ?zh ?birth ?death WHERE {{
  VALUES ?lab {{ {vals} }}
  {{ ?item rdfs:label ?lab }} UNION {{ ?item skos:altLabel ?lab }}
  ?item wdt:P31 wd:Q5 .
  OPTIONAL {{ ?item wdt:P18 ?img }}
  OPTIONAL {{ ?item wdt:P569 ?birth }}
  OPTIONAL {{ ?item wdt:P570 ?death }}
  OPTIONAL {{ ?zhArt schema:about ?item ; schema:isPartOf <https://zh.wikipedia.org/> ;
                     schema:name ?zh }}
}}"""


def _yr(v: str | None) -> int | None:
    """WDQS 的 xsd:dateTime,公元前是前导负号(-0770-01-01T...)。"""
    if not v:
        return None
    s = v.strip()
    neg = s.startswith("-")
    if neg:
        s = s[1:]
    try:
        y = int(s.split("-")[0])
    except ValueError:
        return None
    return -y if neg else y


def chunk(xs: list, n: int):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


def stage_query(people: list[dict], out: pathlib.Path) -> None:
    jl = out / "wikidata_align.jsonl"
    done = set()
    if jl.exists():   # 断点续跑:已出结果的人不再查
        for line in jl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["id"])
        print(f"续跑:已有 {len(done)} 条结果")

    pending = [p for p in people if p["id"] not in done]
    with_cbdb = [p for p in pending if p.get("cbdb")]
    print(f"待查 {len(pending)} 人(其中 {len(with_cbdb)} 人有 CBDB id 可走 L1)")

    results: dict[str, dict] = {}

    # --- L1 CBDB ID
    for i, batch in enumerate(chunk(with_cbdb, BATCH), 1):
        print(f"  L1 批 {i}: {len(batch)} 人")
        by_cbdb: dict[str, dict] = {}
        for p in batch:
            by_cbdb[str(p["cbdb"])] = p
            by_cbdb[str(p["cbdb"]).zfill(7)] = p
        # 同一个 CBDB id 可能命中多个 item:CBDB 曾被批量导入 Wikidata,留下一批
        # 只有 P497 的空壳条目(实测班超命中 Q65818188,无中文条目无图,而真正的
        # 班超条目另有其号)。故先收齐候选再择优 —— 有中文条目 > 有图 > QID 小
        # (Q 号小的通常是更早建立的主条目)。取「最后一条」会随机挑到空壳。
        cands: dict[str, list[dict]] = {}
        for b in sparql(q_by_cbdb(batch)):
            p = by_cbdb.get(b["cbdb"]["value"])
            if not p:
                continue
            cands.setdefault(p["id"], []).append({
                "qid": b["item"]["value"].rsplit("/", 1)[-1],
                "img": b.get("img", {}).get("value"),
                "zh": b.get("zh", {}).get("value"),
            })
        for pid, items in cands.items():
            merged: dict[str, dict] = {}
            for it in items:      # 同一 item 的多行(img/zh 各占一行)先并起来
                m = merged.setdefault(it["qid"], {"qid": it["qid"], "img": None, "zh": None})
                m["img"] = m["img"] or it["img"]
                m["zh"] = m["zh"] or it["zh"]
            best = sorted(merged.values(), key=lambda x: (
                0 if x["zh"] else 1, 0 if x["img"] else 1, int(x["qid"][1:])))[0]
            p = next(q for q in batch if q["id"] == pid)
            results[pid] = {**p, "match": "L1", "qid": best["qid"],
                            "img": best["img"], "zh": best["zh"],
                            "l1_candidates": len(merged)}
        time.sleep(SLEEP)

    # --- L2 中文名。除了 L1 没搞定的,还要捞回「L1 命中了但命中的是空壳」的:
    # CBDB 批量导入在 Wikidata 留下一批只有 P497 的条目,既无中文条目也无图,
    # 对配图和外链两个目的都没用(实测班超即如此,且该 id 只此一个候选)。
    # 这类保留 QID 但继续走 L2 找真身。
    thin = {pid for pid, r in results.items() if not r.get("zh") and not r.get("img")}
    rest = [p for p in pending
            if (p["id"] not in results or p["id"] in thin) and p.get("name")]
    for i, batch in enumerate(chunk(rest, BATCH), 1):
        print(f"  L2 批 {i}: {len(batch)} 人")
        by_name: dict[str, list[dict]] = {}
        for p in batch:
            by_name.setdefault(p["name"], []).append(p)
        # 同名多 item 要先聚起来再判歧义,不能边读边定
        cand: dict[str, dict[str, dict]] = {}
        for b in sparql(q_by_label(batch)):
            lab = b["lab"]["value"]
            qid = b["item"]["value"].rsplit("/", 1)[-1]
            e = cand.setdefault(lab, {}).setdefault(qid, {"qid": qid, "img": None, "zh": None,
                                                          "birth": None, "death": None})
            e["img"] = e["img"] or b.get("img", {}).get("value")
            e["zh"] = e["zh"] or b.get("zh", {}).get("value")
            e["birth"] = e["birth"] or _yr(b.get("birth", {}).get("value"))
            e["death"] = e["death"] or _yr(b.get("death", {}).get("value"))
        for name, ps in by_name.items():
            items = list(cand.get(name, {}).values())
            for p in ps:
                ok = []
                for it in items:
                    # 生卒年任一端对得上(容差内)即认;两端都无从比对的不认 ——
                    # 只凭同名就写进库,等于把「王安」判给随便哪个王安
                    hit = False
                    for mine, theirs in ((p["born"], it["birth"]), (p["died"], it["death"])):
                        if mine is not None and theirs is not None and abs(mine - theirs) <= TOL:
                            hit = True
                    if hit:
                        ok.append(it)
                prev = results.get(p["id"])          # L1 空壳的 QID,兜底留着
                def keep(it, tag):
                    results[p["id"]] = {**p, "match": tag, "qid": it["qid"],
                                        "img": it["img"], "zh": it["zh"]}
                if len(ok) == 1:
                    keep(ok[0], "L2")
                elif len(ok) > 1:
                    results[p["id"]] = {**p, "match": "AMBIG", "qid": prev and prev.get("qid"),
                                        "img": None, "zh": None,
                                        "note": f"{len(ok)} 个候选生卒皆吻合,待人工"}
                elif len(items) == 1:
                    # 生卒年无从比对(我方或对方缺),但该中文名在 Q5 里全库唯一 ——
                    # 唯一精确名匹配本身就是不弱的证据(褒姒/比干这类上古人物两边
                    # 都没有生卒年,一刀切掉等于把它们永远排除)。降一档标记,
                    # 让对账表把它们单独列出来供抽查,不与 L1/L2 混为一谈。
                    keep(items[0], "L2-weak")
                elif prev:
                    results[p["id"]] = prev          # L2 无所获,退回 L1 的空壳 QID
                else:
                    results[p["id"]] = {**p, "match": "NONE", "qid": None,
                                        "img": None, "zh": None}
        time.sleep(SLEEP)

    for p in pending:
        results.setdefault(p["id"], {**p, "match": "NONE", "qid": None, "img": None, "zh": None})

    with jl.open("a", encoding="utf-8") as f:
        for r in results.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"写入 {len(results)} 条 -> {jl}")


# ---------------------------------------------------------------- 复检 + 许可

COMMONS_BATCH = 50   # MediaWiki API 单次 titles 上限(非 bot 账号)


def commons_meta_batch(filenames: list[str]) -> dict[str, dict]:
    """批量取 Commons 文件的许可与作者。CC BY-SA 强制署名,不取回来就没法合规展示。

    必须批量:一文件一请求跑到 100 条就被 429 了(实测「Your bot is making too many
    requests」)。API 允许一次 50 个 titles,439 张图变 9 个请求 —— 既快又不扰民。
    返回按「归一化文件名」索引:API 会把下划线换成空格再回给你,原样查会对不上。
    """
    q = {
        "action": "query", "format": "json", "prop": "imageinfo",
        "iiprop": "extmetadata|url", "iiurlwidth": "400",
        "titles": "|".join(f"File:{n}" for n in filenames),
    }
    txt = _post(COMMONS_API, q, "application/json")   # 50 个标题拼 GET 会超长,用 POST
    d = json.loads(txt)
    out: dict[str, dict] = {}
    for page in (d.get("query", {}).get("pages") or {}).values():
        title = (page.get("title") or "").removeprefix("File:")
        ii = (page.get("imageinfo") or [{}])[0]
        ex = ii.get("extmetadata", {}) or {}
        get = lambda k: (ex.get(k) or {}).get("value")  # noqa: E731
        out[title.replace("_", " ")] = {
            "license": get("LicenseShortName"), "license_url": get("LicenseUrl"),
            "artist": get("Artist"), "credit": get("Credit"),
            "thumb": ii.get("thumburl"), "descurl": ii.get("descriptionurl"),
        }
    return out


def stage_verify(out: pathlib.Path) -> None:
    jl = out / "wikidata_align.jsonl"
    rows = [json.loads(l) for l in jl.read_text(encoding="utf-8").splitlines() if l.strip()]
    vf = out / "wikidata_media.jsonl"
    done = set()
    if vf.exists():
        for l in vf.read_text(encoding="utf-8").splitlines():
            if l.strip():
                m = json.loads(l)
                # 出过错的不算「已完成」:429 那批本来就没拿到许可,续跑时必须重来。
                # 把失败也记成 done 会让它们永远补不上(踩过)。
                if not m.get("error"):
                    done.add(m["id"])
    todo = [r for r in rows if r.get("img") and r["id"] not in done]
    print(f"待复检图像 {len(todo)} 条")
    with vf.open("a", encoding="utf-8") as f:
        for bi, batch in enumerate(chunk(todo, COMMONS_BATCH), 1):
            # P18 的值是 Special:FilePath/<file> 形式,取尾段即文件名
            names = {r["id"]: urllib.parse.unquote(r["img"].rsplit("/", 1)[-1]) for r in batch}
            try:
                metas = commons_meta_batch(list(names.values()))
            except Exception as e:  # noqa: BLE001
                print(f"  ! 批 {bi} 取许可失败: {e}", file=sys.stderr)
                metas = {}
            for r in batch:
                fn = names[r["id"]]
                m = metas.get(fn.replace("_", " ")) or metas.get(fn)
                rec = {"id": r["id"], "name": r["name"], "file": fn}
                rec.update(m if m else {"error": "no metadata"})
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"  {min(bi * COMMONS_BATCH, len(todo))}/{len(todo)}")
            time.sleep(2.0)
    print(f"写入 -> {vf}")


# ---------------------------------------------------------------- 对账表

def stage_report(out: pathlib.Path) -> None:
    jl = out / "wikidata_align.jsonl"
    rows = [json.loads(l) for l in jl.read_text(encoding="utf-8").splitlines() if l.strip()]
    media = {}
    vf = out / "wikidata_media.jsonl"
    if vf.exists():
        for l in vf.read_text(encoding="utf-8").splitlines():
            if l.strip():
                m = json.loads(l)
                media[m["id"]] = m
    csvp = out / "wikidata_align.csv"
    with csvp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name", "生", "卒", "importance", "匹配方式", "QID",
                    "zh条目", "图文件", "许可", "作者", "需人工复核"])
        for r in sorted(rows, key=lambda x: (x.get("importance") or 9, x["id"])):
            m = media.get(r["id"], {})
            w.writerow([
                r["id"], r.get("name"), r.get("born"), r.get("died"), r.get("importance"),
                r.get("match"), r.get("qid") or "", r.get("zh") or "",
                m.get("file", ""), m.get("license", ""),
                (m.get("artist") or "")[:80].replace("\n", " "),
                "Y" if r.get("match") == "AMBIG" else "",
            ])
    tot = len(rows)
    by = {}
    for r in rows:
        by[r.get("match")] = by.get(r.get("match"), 0) + 1
    withimg = sum(1 for r in rows if r.get("img"))
    withzh = sum(1 for r in rows if r.get("zh"))
    print(f"总 {tot} 人")
    for kk, vv in sorted(by.items(), key=lambda x: -x[1]):
        print(f"  {kk}: {vv} ({vv/tot*100:.1f}%)")
    print(f"  带图: {withimg} ({withimg/tot*100:.1f}%)")
    print(f"  带 zh 条目: {withzh} ({withzh/tot*100:.1f}%)")
    print(f"对账表 -> {csvp}")


# ---------------------------------------------------------------- 写回 YAML

# 只写这些许可。CC BY-SA 的 ShareAlike 只约束衍生作品(单纯展示不触发),
# 但署名是硬要求 —— 有 artist 才收。许可字样取不到的一律不收:
# 「不知道能不能用」和「能用」是两回事。
# 实测 439 张的分布:Public domain 390 / CC BY-SA 各版 28 / CC0 6 / CC BY 各版 12 /
# FAL 1 / No restrictions 1 / Attribution 1 —— 全部是自由许可,故全收。
# 但仍逐条记录许可字样与作者:CC BY(-SA) 强制署名,合规责任不能靠「大多是 PD」蒙混。
OK_LICENSE_PREFIX = ("public domain", "cc0", "cc by", "pd-",
                     "fal", "no restrictions", "attribution")


def _license_ok(m: dict) -> bool:
    lic = (m.get("license") or "").strip().lower()
    if not lic:
        return False
    return any(lic.startswith(p) for p in OK_LICENSE_PREFIX)


def stage_apply(out: pathlib.Path, dry: bool) -> None:
    rows = {r["id"]: r for r in
            (json.loads(l) for l in (out / "wikidata_align.jsonl").read_text(
                encoding="utf-8").splitlines() if l.strip())}
    media = {}
    vf = out / "wikidata_media.jsonl"
    if vf.exists():
        for l in vf.read_text(encoding="utf-8").splitlines():
            if l.strip():
                m = json.loads(l)
                media[m["id"]] = m

    stat = {"qid": 0, "zh": 0, "img": 0, "img_skipped_license": 0, "files": 0}
    for f in sorted(PERSONS.glob("*.yaml")):
        raw = f.read_text(encoding="utf-8")
        d = yaml.safe_load(raw) or {}
        r = rows.get(d.get("id"))
        if not r:
            continue
        # AMBIG 一律不写:9 个同名候选生卒皆吻合者留给人工,宁缺毋滥
        if r.get("match") == "AMBIG":
            continue
        add: dict[str, str] = {}
        if r.get("qid"):
            add["wikidata_id"] = r["qid"]
        if r.get("zh"):
            add["wikipedia_zh"] = r["zh"]
        m = media.get(d.get("id")) or {}
        if m.get("thumb"):
            if _license_ok(m):
                # 存 Commons 的缩略图 URL(400px):原图动辄数 MB,档案卡头像用不着,
                # 且 Special:FilePath 那套裸空格 URL 脚本消费时会 000
                add["image"] = m["thumb"]
                add["image_license"] = m.get("license") or ""
                add["image_credit"] = _strip_html(m.get("artist") or "")[:120]
                add["image_source_page"] = m.get("descurl") or ""
            else:
                stat["img_skipped_license"] += 1
        if not add:
            continue
        stat["qid"] += 1 if "wikidata_id" in add else 0
        stat["zh"] += 1 if "wikipedia_zh" in add else 0
        stat["img"] += 1 if "image" in add else 0
        stat["files"] += 1
        if dry:
            continue
        # 逐键改写而非整份 yaml.dump:dump 会重排键序、丢注释、把中文转义成
        # \uXXXX,整个 data/ 的 diff 会变成一片噪声,没法审
        raw = _upsert_keys(raw, add)
        f.write_text(raw, encoding="utf-8")
    print(("[dry-run] " if dry else "") + f"改动 {stat['files']} 个文件:"
          f" wikidata_id {stat['qid']} / wikipedia_zh {stat['zh']} / image {stat['img']}"
          f" (许可不合格跳过 {stat['img_skipped_license']})")


def _strip_html(s: str) -> str:
    """Commons 的 Artist 是 HTML 片段,常见形如
    `<span lang="en">Unknown author</span><span lang="zh">Unknown author</span>`
    —— 多语言各一段。直接去标签会拼成「Unknown authorUnknown author」。
    故按标签边界切开、去重后再接,保序去重(第一次出现的写法优先)。"""
    import re
    parts = [p.strip() for p in re.split(r"<[^>]+>", s)]
    seen, out = set(), []
    for p in parts:
        p = re.sub(r"\s+", " ", p)
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    # 用空格接而非分隔符:去标签后的片段多半是同一句话被内联 <a> 切开的
    # (「Original uploader was」/「Jason22」/「at」/「zh.wikipedia」),
    # 接空格即还原原句;去重只为收拾多语言重复 span 那种情形。
    return " ".join(out)


def _upsert_keys(raw: str, add: dict[str, str]) -> str:
    """就地替换已有顶层键,其余追加到文末。保持原文件的键序与注释不动。"""
    lines = raw.rstrip("\n").split("\n")
    for kk, vv in add.items():
        val = json.dumps(vv, ensure_ascii=False)   # 顺带处理引号/冒号/前导空格
        line = f"{kk}: {val}"
        for i, ln in enumerate(lines):
            if not ln.startswith(kk + ":"):
                continue
            # 老的 image 值是不带引号的裸 URL,里面有空格(Special:FilePath/Li Bai ...),
            # YAML dump 时被折成多行:第二行 `  Wei.jpg` 是续行不是新键。
            # 只换第一行会把续行孤零零留在原地,整个文件当场语法错(tuoba_hong 中招)。
            # 本函数处理的键全是标量,故其后所有缩进行必属该标量,一并吃掉。
            j = i + 1
            while j < len(lines) and lines[j][:1] in (" ", "\t") and lines[j].strip():
                j += 1
            lines[i:j] = [line]
            break
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["query", "verify", "report", "apply"], required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "data" / "_align"))
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 人(调试用)")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    if a.stage == "query":
        ppl = load_people()
        if a.limit:
            ppl = ppl[:a.limit]
        print(f"种子人物 {len(ppl)} 人")
        stage_query(ppl, out)
    elif a.stage == "verify":
        stage_verify(out)
    elif a.stage == "apply":
        stage_apply(out, a.dry_run)
    else:
        stage_report(out)


if __name__ == "__main__":
    main()
