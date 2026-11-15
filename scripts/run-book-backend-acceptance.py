#!/usr/bin/env python3
"""Run a source-safe book benchmark and render a self-contained HTML report."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from html import escape
import json
from pathlib import Path
import sys
import tempfile


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.exploration.acceptance import (  # noqa: E402
    BookBackendAcceptanceResult,
    acceptance_verdict,
    run_book_backend_acceptance,
)
from app.schemas.exploration import ExplorationBrief  # noqa: E402


SERIES_URL = (
    "https://cup.cuhk.edu.hk/chinesepress/promotion/prc_sample/index.htm"
)
VOLUME_URL = (
    "https://cup.cuhk.edu.hk/index.php?product_id=1467&route=product%2Fproduct"
)
SAMPLE_URL = (
    "https://cup.cuhk.edu.hk/chinesepress/promotion/prc_sample/03/"
    "chp-03/chapter.htm"
)


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the history-kb book backend acceptance lane"
    )
    parser.add_argument("--page-text-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--acquisition-duration-ms", type=float, default=0)
    parser.add_argument("--ocr-duration-ms", type=float, default=0)
    return parser.parse_args()


def _load_public_sample(directory: Path) -> tuple[str, list[Path]]:
    pages = sorted(directory.glob("page-*.txt"))
    if not pages:
        raise SystemExit(f"No page-*.txt files found in {directory}")
    sections = ["# 《中华人民共和国史》第三卷官方公开样阅"]
    for page in pages:
        page_number = page.stem.rsplit("-", 1)[-1]
        sections.append(
            f"## 公开样阅页 {page_number}\n\n{page.read_text(encoding='utf-8')}"
        )
    return "\n\n".join(sections), pages


def _ocr_metrics(
    directory: Path, pages: list[Path]
) -> dict[str, float | int | bool | None]:
    scored = 0
    low = 0
    confidence_sum = 0.0
    expected_tsv = {path.with_suffix(".tsv") for path in pages}
    present_tsv = set(directory.glob("page-*.tsv"))
    paired_tsv = sorted(expected_tsv & present_tsv)
    for path in paired_tsv:
        with path.open(encoding="utf-8", errors="replace", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                try:
                    confidence = float(row.get("conf", "-1"))
                except ValueError:
                    continue
                if confidence < 0:
                    continue
                scored += 1
                confidence_sum += confidence
                low += confidence < 60
    return {
        "scored_tokens": scored,
        "average_confidence": round(confidence_sum / scored, 2) if scored else None,
        "low_confidence_tokens": low,
        "low_confidence_rate": round(low / scored, 4) if scored else None,
        "expected_pages": len(pages),
        "paired_pages": len(paired_tsv),
        "pairing_complete": bool(expected_tsv == present_tsv),
    }


def _pill(status: str) -> str:
    label = {"pass": "通过", "fail": "失败", "not_run": "未运行"}[status]
    return f'<span class="pill {status}">{label}</span>'


def _render_report(
    *,
    result: dict,
    page_count: int,
    ocr: dict,
    acquisition_duration_ms: float,
    ocr_duration_ms: float,
) -> str:
    result_model = BookBackendAcceptanceResult.model_validate(result)
    checks = result["checks"]
    control_checks = [item for item in checks if item["status"] != "not_run"]
    passed = sum(item["status"] == "pass" for item in control_checks)
    control_summary = (
        "可恢复、可复核、NoModel 不编造、SQLite 未发现来源抽样片段、删除可清理。"
        if passed == len(control_checks)
        else f"存在 {len(control_checks) - passed} 项失败；必须先处理下表失败项。"
    )
    control_conclusion = (
        "本轮在强制 NoModel 的范围内证明了控制面不会编造，且能够恢复、复核和删除。"
        if passed == len(control_checks)
        else "本轮没有证明控制面可靠；失败项必须修复并重新执行验收。"
    )
    argument_skipped = "argument_extraction" in result["skipped_passes"]
    routing_status = "fail" if argument_skipped else "pass"
    overall = acceptance_verdict(
        result_model,
        routing_failed=argument_skipped,
    )
    overall_label = {
        "pass": "通过",
        "conditional": "有条件通过",
        "failed": "未通过",
    }[overall]
    routing_detail = (
        "公开样阅具有明显的论证组织，但系统将其主类型判为事件叙事，并跳过论证提取。"
        if argument_skipped
        else "本次样本保留了论证提取路径。"
    )
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    embedded = {
        "generated_at": generated_at,
        "case": {
            "series": "中华人民共和国史（1949—1981）",
            "volume": "第三卷：思考与选择（1956—1957）",
            "author": "沈志华",
            "public_sample_pages": page_count,
            "source_urls": [SERIES_URL, VOLUME_URL, SAMPLE_URL],
        },
        "acquisition": {
            "metric_provenance": "operator_supplied_durations",
            "asset_duration_ms": acquisition_duration_ms,
            "ocr_duration_ms": ocr_duration_ms,
            **ocr,
        },
        "backend": result,
        "assessment": {
            "control_plane": f"{passed}/{len(control_checks)} pass",
            "routing": routing_status,
            "content_quality": "not_run",
            "overall": overall,
        },
    }
    embedded_json = json.dumps(
        embedded, ensure_ascii=False, sort_keys=True
    ).replace("</", "<\\/")
    checks_html = "".join(
        "<tr>"
        f"<td>{_pill(item['status'])}</td>"
        f"<td><code>{escape(item['code'])}</code></td>"
        f"<td>{escape(item['detail'])}</td>"
        "</tr>"
        for item in checks
    )
    pass_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{count}</td></tr>"
        for name, count in result["selected_passes"].items()
    )
    skipped = ", ".join(
        f"{name}（{reason}）" for name, reason in result["skipped_passes"].items()
    )
    low_rate = ocr.get("low_confidence_rate")
    low_rate_text = f"{low_rate * 100:.2f}%" if isinstance(low_rate, float) else "未测"
    avg_conf = ocr.get("average_confidence")
    avg_conf_text = f"{avg_conf:.2f}" if isinstance(avg_conf, float) else "未测"
    acquisition_text = (
        f"{acquisition_duration_ms / 1000:.1f} 秒"
        if acquisition_duration_ms
        else "未记录"
    )
    ocr_time_text = f"{ocr_duration_ms / 1000:.1f} 秒" if ocr_duration_ms else "未记录"
    short_digest = result["source_checksum"][:16]

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>《中华人民共和国史》后端验收执行报告</title>
<style>
:root {{ --paper:#f3efe4; --ink:#17212b; --muted:#69717b; --line:#d7cfbd;
  --red:#b64a37; --green:#286a55; --amber:#a27623; --navy:#20354a; }}
* {{ box-sizing:border-box }}
body {{ margin:0; color:var(--ink); background:var(--paper); font-family:-apple-system,
  BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif;
  line-height:1.62; }}
main {{ max-width:1180px; margin:auto; padding:44px 28px 80px; }}
.eyebrow {{ color:var(--red); font-size:12px; letter-spacing:.16em; font-weight:700; }}
h1 {{ max-width:900px; margin:10px 0 12px; font:700 clamp(32px,5vw,66px)/1.08 Georgia,
  "Noto Serif SC",serif; letter-spacing:-.035em; }}
h2 {{ margin:0 0 18px; font:700 25px/1.2 Georgia,"Noto Serif SC",serif; }}
h3 {{ margin:0 0 8px; font-size:16px; }}
p {{ margin:0 0 12px; }} a {{ color:var(--red); }}
.lede {{ max-width:840px; color:#4b5560; font-size:18px; }}
.verdict {{ margin:30px 0; padding:22px 24px; display:grid; grid-template-columns:180px 1fr;
  gap:24px; border:1px solid var(--line); background:rgba(255,255,255,.42); }}
.verdict strong {{ font:700 30px/1.1 Georgia,"Noto Serif SC",serif; color:var(--amber); }}
.grid {{ display:grid; grid-template-columns:repeat(12,1fr); gap:16px; margin:22px 0; }}
.card {{ grid-column:span 4; border:1px solid var(--line); background:rgba(255,255,255,.36);
  padding:20px; min-height:130px; }}
.wide {{ grid-column:span 8; }} .full {{ grid-column:1/-1; }}
.metric {{ font:700 30px/1 Georgia,"Noto Serif SC",serif; margin:8px 0; }}
.muted {{ color:var(--muted); font-size:13px; }}
section {{ margin-top:52px; }}
table {{ width:100%; border-collapse:collapse; background:rgba(255,255,255,.25); }}
th,td {{ text-align:left; vertical-align:top; padding:12px 14px; border-bottom:1px solid var(--line); }}
th {{ color:var(--muted); font-size:12px; letter-spacing:.08em; }}
code {{ font-family:"SFMono-Regular",Consolas,monospace; font-size:12px; }}
.pill {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px;
  font-weight:700; white-space:nowrap; }}
.pass {{ color:var(--green); background:#dcebe4; }} .fail {{ color:var(--red); background:#f1dcd6; }}
.not_run {{ color:var(--amber); background:#eee4c9; }}
.flow {{ display:grid; grid-template-columns:repeat(7,1fr); gap:8px; align-items:stretch; }}
.flow div {{ min-height:84px; padding:12px 10px; border:1px solid var(--line); background:#faf7ef;
  position:relative; font-size:13px; }}
.flow div:not(:last-child)::after {{ content:"→"; position:absolute; right:-13px; top:31px;
  z-index:2; color:var(--red); font-weight:700; }}
.flow b {{ display:block; margin-bottom:6px; }}
.timeline {{ border-left:2px solid var(--line); margin-left:8px; padding-left:24px; }}
.step {{ position:relative; margin:0 0 24px; }}
.step::before {{ content:""; position:absolute; left:-31px; top:7px; width:12px; height:12px;
  border-radius:50%; background:var(--paper); border:3px solid var(--red); }}
.issue {{ border-top:1px solid var(--line); padding:18px 0; display:grid;
  grid-template-columns:70px 230px 1fr; gap:12px; }}
.sev {{ color:var(--red); font-weight:800; }}
.note {{ border-left:4px solid var(--amber); padding:16px 18px; background:#eee7d7; }}
.source-list li {{ margin:9px 0; }}
footer {{ margin-top:60px; padding-top:22px; border-top:1px solid var(--line); color:var(--muted);
  font-size:12px; }}
@media (max-width:800px) {{ .card,.wide {{ grid-column:1/-1; }} .verdict {{ grid-template-columns:1fr; }}
  .flow {{ grid-template-columns:1fr; }} .flow div:not(:last-child)::after {{ content:"↓"; right:auto;
  left:18px; top:auto; bottom:-18px; }} .issue {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body><main>
<div class="eyebrow">HISTORY-KB · BACKEND ACCEPTANCE · {escape(generated_at)}</div>
<h1>用《中华人民共和国史》检验：后端是否真的理解一本复杂历史著作？</h1>
<p class="lede">这不是产品演示稿，而是一次带来源边界、运行证据和失败项的真实验收。样本来自香港中文大学出版社公开样阅；原图与 OCR 原文没有写入仓库，也没有进入本报告。</p>

<div class="verdict"><strong>{escape(overall_label)}</strong><div>
  <p><b>控制面 {passed}/{len(control_checks)} 通过：</b>{escape(control_summary)}</p>
  <p><b>内容智能不通过发布验收：</b>本轮强制 NoModel；更重要的是，短篇 OCR 样阅被路由成 <code>{escape(result['primary_book_type'])}</code>，论证提取被跳过。现在还不能声称系统已经拆解了这本书。</p>
</div></div>

<div class="grid">
  <article class="card"><div class="muted">官方公开样阅</div><div class="metric">{page_count} 页</div><div>第三卷第八章内页样本</div></article>
  <article class="card"><div class="muted">解析结果</div><div class="metric">{result['paragraph_count']} 段</div><div>{result['character_count']} 字符 · {result['section_count']} 节</div></article>
  <article class="card"><div class="muted">OCR 质量</div><div class="metric">{avg_conf_text}</div><div>{low_rate_text} 词元低于 60</div></article>
  <article class="card"><div class="muted">规划规模</div><div class="metric">{result['planned_work_item_count']}</div><div>候选任务；并发上限由计划约束</div></article>
  <article class="card"><div class="muted">本地处理</div><div class="metric">{result['processing_duration_ms']:.1f} ms</div><div>无远程模型的控制面执行</div></article>
  <article class="card"><div class="muted">来源指纹</div><div class="metric" style="font-size:18px">{escape(short_digest)}…</div><div>只记录 SHA-256，不展示原文</div></article>
</div>

<section><h2>验收对象</h2>
<div class="grid">
  <article class="card wide"><div class="muted">十卷本书系 · 1949—1981</div>
    <h3 style="font:700 24px/1.35 Georgia,'Noto Serif SC',serif;margin-top:8px">第三卷《思考与选择——从知识分子会议到反右派运动（1956—1957）》</h3>
    <p>沈志华著 · 香港中文大学出版社 · 2008 年 5 月 · 846 页 · 精装 ISBN 978-988-17562-3-7</p>
  </article>
  <article class="card"><div class="muted">本轮输入边界</div><div class="metric">第八章</div>
    <div>出版社公开 {page_count} 页内页；OCR 未人工逐字校订</div>
  </article>
</div></section>

<section><h2>为什么它是更好的长期用例</h2>
<div class="grid">
  <article class="card"><h3>多卷本，不是单文件</h3><p>书系跨 1949—1981 年，由多位作者分卷撰写，天然要求“书系—卷—章—页—段落”的分层来源模型。</p></article>
  <article class="card"><h3>事实与作者解释并存</h3><p>第三卷既组织事件过程，也使用档案、报刊、口述与回忆材料提出解释；不能把作者判断压扁成事实清单。</p></article>
  <article class="card"><h3>跨时空与制度网络</h3><p>人物、会议、政策、机构与地区响应形成网络，适合同时检验时间柱、地图、论证图和证据关系。</p></article>
</div>
<p class="note">最佳用例不等于默认公开全文。此基准只使用出版社公开样阅；未来接入完整合法副本时，仍应保持本地私有来源、引用定位与公开投影分离。</p></section>

<section><h2>本次真实运行链路</h2>
<div class="flow">
  <div><b>1 · 官方核验</b>书系、卷名、作者、ISBN、出版信息</div>
  <div><b>2 · 样阅获取</b>{page_count} 张公开内页<br>{escape(acquisition_text)}</div>
  <div><b>3 · OCR 桥接</b>繁体中文识别<br>{escape(ocr_time_text)}</div>
  <div><b>4 · 私有导入</b>Markdown 临时源<br>稳定段落锚点</div>
  <div><b>5 · 类型路由</b>{escape(result['primary_book_type'])}<br>{result['classification_confidence']:.1%}</div>
  <div><b>6 · Worker</b>{' → '.join(escape(x) for x in result['state_sequence'])}</div>
  <div><b>7 · 清理</b>删除探索<br>保险库消失</div>
</div></section>

<section><h2>控制面验收</h2>
<table><thead><tr><th>状态</th><th>检查</th><th>证据</th></tr></thead><tbody>{checks_html}</tbody></table>
</section>

<section><h2>类型路由：本轮最重要的失败</h2>
<div class="grid">
  <article class="card wide"><h3>{_pill(routing_status)} {escape(routing_detail)}</h3>
    <p>系统给出 <code>{escape(result['primary_book_type'])}</code>，置信度 {result['classification_confidence']:.3f}；
    <code>argumentative_monograph</code> 得分 {result['type_scores'].get('argumentative_monograph', 0):.3f}。
    不确定性：{escape(', '.join(result['routing_uncertainties']) or '无')}。</p>
    <p>这暴露了一个产品级问题：只有 {page_count} 页 OCR 内页时，日期与人物密度会压过论证结构信号；现有路由随即跳过论证提取，正好错过这本书最有价值的部分。</p>
  </article>
  <article class="card"><h3>被跳过</h3><p>{escape(skipped)}</p></article>
</div>
<details><summary>查看本次选择的 Pass 数量</summary><table><tbody>{pass_rows}</tbody></table></details>
</section>

<section><h2>监控记录与反思</h2>
<div class="timeline">
  <div class="step"><h3>来源检索没有被误判成内容缺失</h3><p>本机 Downloads/Documents 未发现对应文件；微信读书工具因本地技能版本要求升级且下载授权超时，记为“环境未核验”，随后改用出版社官方公开样阅，没有据此宣称书不存在。</p></div>
  <div class="step"><h3>外部获取是最大耗时点</h3><p>{page_count} 个小型公开图片资源的浏览器资产打包耗时 {escape(acquisition_text)}，远高于 OCR 的 {escape(ocr_time_text)} 和本地后端的 {result['processing_duration_ms']:.1f} ms。采集与 OCR 时长是运行者提供的外部观测值，机器记录另行标注其来源；生产流程必须为每个外部阶段设置独立超时、进度事件和可恢复 checkpoint。</p></div>
  <div class="step"><h3>并行审计发生上下文污染</h3><p>一次复用的审计 Agent 误执行了旧的一次性通知任务。幂等标记阻止了重复外部动作，但本轮审计没有完成；主流程及时移出依赖链。以后必须为跨任务 worker 使用全新、无历史上下文的任务，并校验首个 checkpoint 是否匹配 run_id。</p></div>
  <div class="step"><h3>“质量门通过”不代表“内容正确”</h3><p>零主张、零事件时，引用完整性等门仍可形式上通过，因为没有对象可违反约束。报告因此把 <code>explicit_no_model</code> 视为安全通过，却把内容质量明确标为未运行。</p></div>
</div></section>

<section><h2>明显缺陷与下一轮实现顺序</h2>
<div class="issue"><div class="sev">P0</div><h3>来源状态缺失</h3><p>增加 <code>rendered → ocr_unverified → ocr_reviewed</code> 状态与逐页置信度；低置信字符必须回看图像，不能直接成为事实锚点。</p></div>
<div class="issue"><div class="sev">P0</div><h3>类型路由会误删能力</h3><p>书目元数据、用户声明与正文信号应共同形成带不确定度的类型先验；出现 <code>close_type_scores</code> 时运行多路 Pass，不应直接跳过论证提取。</p></div>
<div class="issue"><div class="sev">P0</div><h3>单文档模型不足</h3><p>引入 Series / Volume / Chapter / Page / Passage 层级与跨卷 synthesis；每个洞见必须能回到卷、章、页图与段落锚点。</p></div>
<div class="issue"><div class="sev">P0</div><h3>真实内容验收未运行</h3><p>在明确的数据出境边界下配置模型通道，建立人工金标：主张归因、作者判断、事件时序、人物同一性、地点解析、反证缺口分别计分。</p></div>
<div class="issue"><div class="sev">P1</div><h3>观测仍不够完整</h3><p>为采集、OCR、分段、每个 Pass、复核和投影记录开始/结束、输入输出计数、摘要哈希、重试原因与成本；日志不得保存原文。</p></div>
<div class="issue"><div class="sev">P1</div><h3>观点结构不能二元化</h3><p>固定区分“作者判断 / 书内材料 / 平台推断 / 其他研究”，只在真实冲突存在时建立反方关系，不强行生成正反观点。</p></div>
</section>

<section><h2>结论</h2>
<p>《中华人民共和国史》适合作为 history-kb 的长期黄金验收集，尤其适合暴露多卷层级、复杂论证、时空网络与来源归因问题。{escape(control_conclusion)} 无论控制面结果如何，当前类型路由与来源状态都还不足以承担“真实拆书”的核心承诺。</p>
<p><b>准入标准：</b>修复多路类型路由与 OCR 状态后，再用合法完整副本运行真实模型金标评测；在作者判断归因、事件时间、引用跳转和跨卷综合均达标前，不将其标为“已支持”的公开 demo。</p>
</section>

<section><h2>来源</h2><ul class="source-list">
  <li><a href="{SERIES_URL}">香港中文大学出版社：书系官方介绍与分卷目录</a></li>
  <li><a href="{VOLUME_URL}">香港中文大学出版社：第三卷产品页</a></li>
  <li><a href="{SAMPLE_URL}">香港中文大学出版社：第三卷官方公开样阅入口</a></li>
</ul></section>

<footer>生成时间 {escape(generated_at)} · 机器记录已内嵌在本文件的 <code>script#run-data</code> 中 · 报告不含书籍原图、OCR 原文、凭证或本机临时路径。</footer>
<script id="run-data" type="application/json">{embedded_json}</script>
</main></body></html>"""


def main() -> int:
    args = _args()
    if args.acquisition_duration_ms < 0 or args.ocr_duration_ms < 0:
        raise SystemExit("duration metrics must be non-negative")
    content, pages = _load_public_sample(args.page_text_dir)
    ocr = _ocr_metrics(args.page_text_dir, pages)
    with tempfile.TemporaryDirectory(prefix="history-kb-book-acceptance-") as state_dir:
        result = run_book_backend_acceptance(
            content=content,
            state_dir=state_dir,
            title="中华人民共和国史 第三卷：思考与选择",
            author="沈志华",
            version_label=(
                f"香港中文大学出版社官方公开样阅（{len(pages)}页，OCR未复核）"
            ),
            brief=ExplorationBrief(
                question="作者如何解释1957年党内整风转向反右派运动？",
                time_range="1956—1957",
                geography=["中国"],
                threads=["政策转向", "知识分子", "政治动员", "证据方法"],
                status="confirmed",
            ),
        ).model_dump(mode="json")
    report = _render_report(
        result=result,
        page_count=len(pages),
        ocr=ocr,
        acquisition_duration_ms=args.acquisition_duration_ms,
        ocr_duration_ms=args.ocr_duration_ms,
    )
    result_model = BookBackendAcceptanceResult.model_validate(result)
    routing_failed = "argument_extraction" in result["skipped_passes"]
    overall = acceptance_verdict(result_model, routing_failed=routing_failed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "overall": overall,
                "control_checks": result["checks"],
                "routing": {
                    "primary_book_type": result["primary_book_type"],
                    "classification_confidence": result[
                        "classification_confidence"
                    ],
                    "argument_extraction_skipped": (
                        "argument_extraction" in result["skipped_passes"]
                    ),
                },
            },
            ensure_ascii=False,
        )
    )
    return 2 if overall == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
