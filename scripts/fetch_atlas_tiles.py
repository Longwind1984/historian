#!/usr/bin/env python3
"""抓取谭其骧《中国历史地图集》瓦片到 data/geo/atlas_tiles/,供后端自托管。

为什么要自己存一份:tile.osgeo.cn 那台 nginx 对 curl(GET 与 OPTIONS 都试过)稳定返回
Access-control-allow-origin: *,但 Chromium 里 maplibre 取瓦片必报
"blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present",
而同一浏览器同一 URL 用裸 <img> 加载却 30~121ms 成功(img 不校验 CORS)。
差异不在可达性,在 CORS —— 那台服务器我们控制不了,这个差异也无法从外部诊断到底。
底图是产品功能,不该挂在这样的单点上。

图层 id 的年代归属是逐幅取瓦片看图认出来的 —— 该服务 10714 个图层的 Title 就是 id 本身、
Abstract 空、bbox 全是全球默认,demo 目录页只列 id。认图依据见 SHEETS 的注释,
与 frontend/src/components/map/MapPanel.vue 的 ATLAS_SHEETS 一一对应(改一处要改两处)。

幂等:已存在且非空的瓦片跳过。并发 4、单 URL 不重试；同主机出现网络故障后
立即熔断尚未开始的任务并标 needs-verification，避免外部服务失联时长时间挂起。
用法:
  全量/指定幅抓取  python3 scripts/fetch_atlas_tiles.py [--zoom-max 6] [--sheets mp051b,mp0500]
  探针认图         uv run --with pillow python3 scripts/fetch_atlas_tiles.py --probe mp051b
                   (抓该幅 z5 中国范围瓦片,PIL 拼预览到 /tmp/atlas_probe/<sid>_z5.png,
                    打印覆盖/空白统计;本地已有瓦片直接复用,不重复请求)
"""
import argparse
import concurrent.futures as cf
import math
import pathlib
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request

# 与 MapPanel.vue 的 ATLAS_SHEETS 对应。认图依据写在注释里,都是直接读图上的地名。
# v3 M9 注册波:汉至清 15 幅新注册(图例纪年/图上地名亲读,详见 MapPanel.vue 与 WORKLOG)。
SHEETS = [
    ("mp0302", "原始社会遗址"),   # 红黑点遗址分布 + 现代地名
    ("mp0305", "夏"),            # 有仍/有虞/安邑/晋阳/平阳
    ("mp0306", "商"),            # 亳/奄/鬼方/土方/林方/羌方
    ("mp0308", "西周"),          # 宗周/成周/曲沃/严允(犬戎)
    ("mp030b", "春秋"),          # 林胡/义渠/绵诸/翟/中山
    ("mp0311", "战国"),          # 楼烦/林胡 + 郡制
    ("mp031f", "秦"),            # 内史/陇西郡/北地郡/上郡/咸阳
    ("mp0324", "西汉"),          # 图例都城=长安;西域都护府/匈奴/乌孙(v3 M9 注册)
    ("mp0334", "东汉"),          # 图例都城=雒阳;西域长史府/鲜卑/夫余(v3 M9 注册)
    ("mp0346", "三国"),          # 图例纪年「魏景元三年…吴永安五年(262年)」;魏/蜀/吴(v3 M9)
    # 勘察曾误判「西汉重复幅」,亲读图例更正:纪年「太康二年(281年)」、都城=洛阳 = 西晋。
    ("mp035a", "西晋"),          # 太康二年281;西域长史府/鲜卑/高昌戊己校尉(v3 M9 新发现)
    ("mp0373", "前秦"),          # 「前」+ 凉州/秦州/长安/梁州
    # 图题纪年「…光初十年、…建兴十五年(327年)」;晋/赵/成/凉/代。
    ("mp0375", "东晋 · 十六国"),  # 327年快照(v3 M9 注册)
    ("mp0391", "北魏"),          # 沃野/武川/怀朔/薄骨律 六镇
    ("mp0393", "西魏"),          # 「西魏」+ 灵州/夏州/长安;年代表区间已收窄 535-557(v3 M9)
    # 图例纪年「陈太建四年、齐武平三年、周建德元年(572年)」;齐/周/陈/突厥/吐谷浑。
    ("mp0394", "北周 · 北齐 · 陈"),  # 572年快照(v3 M9 注册)
    ("mp03c9", "隋"),            # 「隋」+ 灵武郡/京兆郡 郡制
    # 唐三幅分期(v3 M9,图例纪年亲读)。db:勘察曾标「开元741」,更正为总章二年(669)。
    ("mp03db", "唐 · 前期"),      # 总章二年669:单于都护府/安西四镇(焉耆镇/龟兹镇)/吐蕃/大非川
    # dc 复核:与 dd 不同期 —— 突厥牙帐+回纥/同罗/契苾/仆骨(后突厥期)+都城西京+道级驻所,
    # 定开元二十九年(741);年代表改挂 705-755(原 618-906 由 db/dc/dd 三幅分拆)。
    ("mp03dc", "唐 · 中期"),      # 开元二十九年741:突厥牙帐/回纥/西京/河南府/碎叶
    ("mp03dd", "唐 · 后期"),      # 元和十五年820:回鹘牙帐/契丹/奚/西受降城/各方镇(v3 M9 注册)
    # 定谳(v3 T9.4c,探针拼图亲读):图例纪年「(后)晋天福八年(943)」= 五代后晋,非宋初。
    # 定难军/党项 + 府州名,无宋代路名(永兴军路等)。预览图曾存 /tmp/atlas_probe/mp0500_z5.png。
    ("mp0500", "五代十国"),       # 后晋天福八年(943):定难/党项 + 京兆府/凤翔府
    ("mp0503", "北宋 · 辽"),      # 东京开封府/北京大名府/契丹(辽)/西夏/定难军(v3 M9 注册)
    # 西夏区域图(1038-1227)——不入年代表(v3 M9):960-1279 已被 mp0503/053d/053e 全图覆盖。
    # 条目保留备查;实测 156/172 瓦片 <2KB、内容只在河套(z6 x51-52/y23-24),非宋全图(v3 T9.4a)。
    ("mp051b", "西夏 · 区域图"),  # 「夏」兴庆府 + 永兴军路/秦凤路
    # 金南宋全图两幅分期(勘察曾标「同期重复版取一」,亲读图例纪年更正为两期,均入年代表)。
    ("mp053d", "金 · 南宋"),      # 金皇统二年、南宋绍兴十二年(1142):金/西夏兴庆府/开封府/归德府
    ("mp053e", "金 · 南宋"),      # 金泰和八年、南宋嘉定元年(1208):金/西夏/南京路
    # 元全图不存在于 mp05xx(S1+S2 勘察穷尽,只有分省/宣政院/西域区域图),年代表 1280-1367 留兜底。
    ("mp0589", "明 · 前期"),      # 宣德八年(1433):鞑靼/瓦剌/奴儿干都司/亦力把里(v3 M9 注册)
    ("mp058a", "明 · 后期"),      # 万历十年(1582):鞑靼土默特部/亦力把里(v3 M9 注册)
    # 清两幅图例纪年定年(z6 台湾/外东北探针因服务器 SSL 断连失败,改读图例纪年行)。
    ("mp05c1", "清 · 前期"),      # 嘉庆二十五年(1820):外东北/台湾府完整(v3 M9 注册)
    ("mp05d1", "清 · 晚期"),      # 光绪三十四年(1908):外东北已失/台湾已割(v3 M9 注册)
]

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "geo" / "atlas_tiles"
BASE = "https://tile.osgeo.cn/wmts/{sid}/webmercator/{z}/{x}/{y}.png"
# 中国范围。z2-6 够看全国到省级;再往下每级瓦片数 ×4,z7 就要 +112MB,不值。
BBOX = (73.0, 136.0, 18.0, 54.0)   # west, east, south, north


def tiles_for(z, bbox=BBOX):
    w, e, s, n = bbox

    def xy(lon, lat):
        rad = math.radians(lat)
        return (int((lon + 180) / 360 * 2 ** z),
                int((1 - math.log(math.tan(rad) + 1 / math.cos(rad)) / math.pi) / 2 * 2 ** z))

    x0, y0 = xy(w, n)
    x1, y1 = xy(e, s)
    return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE
FETCH_TIMEOUT_S = 8
_fetch_abort = threading.Event()


def fetch(job):
    sid, z, x, y = job
    p = OUT / sid / str(z) / str(x) / f"{y}.png"
    if p.exists() and p.stat().st_size > 500:
        return 0                      # 已有
    if _fetch_abort.is_set():
        return -2                     # 同主机已网络失败；队列熔断
    url = BASE.format(sid=sid, z=z, x=x, y=y)
    try:
        with urllib.request.urlopen(url, timeout=FETCH_TIMEOUT_S, context=_ctx) as r:
            b = r.read()
    except urllib.error.HTTPError:
        return -1                     # 404 等是单片缺失，不代表主机失联
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError):
        _fetch_abort.set()
        return -2
    if len(b) < 100:
        return -1                     # 空瓦片(该幅不覆盖此处),不写盘
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)
    return len(b)


def probe(sid, workers=4):
    """探针模式:抓 sid 的 z5 中国 BBOX 瓦片,PIL 拼一张预览图供肉眼认图。

    sid 不限于 SHEETS 表 —— 勘察未注册图幅正是本模式的用途。抓取的瓦片同样落盘
    OUT/sid/z5/(幂等复用),日后注册该幅时无需重抓。
    """
    from PIL import Image

    _fetch_abort.clear()
    z = 5
    tiles = tiles_for(z)
    jobs = [(sid, z, x, y) for (x, y) in tiles]
    print(f"探针 {sid}: z{z} 中国范围 {len(jobs)} 个瓦片,并发 {workers}(已有本地瓦片跳过)")
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(fetch, jobs))
    unavailable = sum(1 for result in results if result == -2)
    if unavailable:
        print(f"needs-verification: 图砖主机网络调用失败，已熔断 {unavailable} 个探针任务；"
              "本轮不重试同一 URL", file=sys.stderr)
        raise SystemExit(2)

    xs = [x for x, _ in tiles]
    ys = [y for _, y in tiles]
    x0, y0 = min(xs), min(ys)
    w, h = (max(xs) - x0 + 1) * 256, (max(ys) - y0 + 1) * 256
    canvas = Image.new("RGB", (w, h), (238, 234, 226))   # 近纸底色,无片区一眼可辨
    full = small = 0
    for x, y in tiles:
        p = OUT / sid / str(z) / str(x) / f"{y}.png"
        if not p.exists():
            continue
        # 该服务对不覆盖的区域返回极小占位图;2KB 界线沿用 mp051b 实测分析口径
        if p.stat().st_size >= 2048:
            full += 1
        else:
            small += 1
        canvas.paste(Image.open(p), ((x - x0) * 256, (y - y0) * 256))
    none = len(tiles) - full - small

    out_dir = pathlib.Path("/tmp/atlas_probe")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{sid}_z{z}.png"
    canvas.save(out)
    print(f"预览 {out}({w}×{h}) —— 内容片(≥2KB) {full} / 近空白(<2KB) {small} / "
          f"无片 {none},共 {len(tiles)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zoom-max", type=int, default=6)
    ap.add_argument("--workers", type=int, default=4,
                    help="别调高 —— 这是别人的免费服务")
    ap.add_argument("--sheets", type=str, default=None,
                    help="只抓指定图幅,逗号分隔(如 mp051b,mp0500);默认全表")
    ap.add_argument("--probe", type=str, default=None, metavar="SID",
                    help="探针模式:抓该幅 z5 中国范围瓦片并拼预览图到 /tmp/atlas_probe/")
    a = ap.parse_args()

    _fetch_abort.clear()
    if a.probe:
        probe(a.probe, a.workers)
        return

    sheets = SHEETS
    if a.sheets:
        wanted = a.sheets.split(",")
        unknown = [s for s in wanted if s not in dict(SHEETS)]
        if unknown:
            print(f"✗ 未知图幅 id: {', '.join(unknown)}"
                  f"(已登记: {', '.join(dict(SHEETS))};勘察新幅请用 --probe)", file=sys.stderr)
            sys.exit(1)
        sheets = [(sid, name) for sid, name in SHEETS if sid in wanted]

    jobs = [(sid, z, x, y)
            for sid, _ in sheets
            for z in range(2, a.zoom_max + 1)
            for (x, y) in tiles_for(z)]
    print(f"{len(sheets)} 幅 × z2-{a.zoom_max} = {len(jobs)} 个瓦片,并发 {a.workers}")

    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        res = list(ex.map(fetch, jobs))
    new = sum(1 for r in res if r > 0)
    skip = sum(1 for r in res if r == 0)
    bad = sum(1 for r in res if r < 0)
    unavailable = sum(1 for r in res if r == -2)
    size = sum(r for r in res if r > 0)
    print(f"新增 {new}(共 {size/1024/1024:.1f} MB) / 已有 {skip} / 失败或空 {bad} "
          f"—— 耗时 {time.time()-t0:.0f}s")
    if unavailable:
        print(f"needs-verification: 图砖主机网络调用失败，已熔断 {unavailable} 个任务；"
              "本轮不重试同一 URL", file=sys.stderr)
        sys.exit(2)
    if bad > len(jobs) * 0.2:
        print(f"✗ 失败率 {bad/len(jobs)*100:.0f}% 偏高,检查网络或该服务是否变更", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
