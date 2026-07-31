# PROGRESS · 互动历史知识库 · 中国古代史(全朝代 + CBDB/CHGIS 学术增强)

> **历史构建日志**：本文主体停在 phase 16（7,011 实体 / 9,909 关系），保留当时的可重现过程，
> 不再作为当前规模口径。当前状态以 `README.md`、`WORKLOG.md` 与 `handoff.json` 为准：
> 截至 2026-07-22 为 7,396 实体 / 10,266 关系，最新完成 M14，tag `v1.2.1`。

> Build log for the construction of a museum-grade interactive knowledge base of **complete Chinese history**, spanning from Qin (BC 221) to Qing (1912) — approximately 2100 years.

## Status: ✅ COMPLETE + ACADEMIC ENRICHMENT

**最终规模:**

| 阶段 | 实体 | 关系 | 人物 | 地点 | 政权 |
|---|---|---|---|---|---|
| 五代十国 demo + 全朝代覆盖 (phase 0-14) | 1,110 | 899 | 419 | 448 | 51 |
| **+ CBDB 学术增强** (phase 15) | **+5,901** | **+9,010** | **+4,892** | **+1,005** | +4 |
| **+ CHGIS 疆域 GeoJSON** (phase 16) | +18 GeoJSON | — | — | — | — |
| **合计** | **7,011** | **9,909** | **5,311** | **1,453** | **55** |

---

## 数据来源

| 数据源 | 版本 | 用途 |
|---|---|---|
| **CBDB** China Biographical Database (Harvard) | 2026-07-04 SQLite release | 人物/亲属/社交/官职/籍贯 |
| **CHGIS** China Historical GIS (Harvard + Fudan) | V5 (2012) 府级时间序列多边形 | 各朝代疆域 GeoJSON |
| 二十四史 + 资治通鉴 + 续资治通鉴长编 | — | 人工 curated 种子数据 |
| 内置史识(Agent 输出) | — | 跨朝代填充 |

---

## Coverage by era (按朝代覆盖)

| 朝代 | 时期 | 主要人物 | 地图多边形(代表年代) | 状态 |
|---|---|---|---|---|
| 秦 (BC 221-207) | 战国末 + 秦 | 秦始皇、李斯、王翦、蒙恬、陈胜、项羽、刘邦 | 7 (BC 218) | ✅ |
| 西汉 (BC 202-9) | 高祖→王莽 | 刘邦、文帝、景帝、武帝、卫青、霍去病、张骞、董仲舒、司马迁 | 71 (BC 100) | ✅ |
| 新 (9-23) | 王莽 | 王莽、刘秀(起兵前) | 14 | ✅ |
| 东汉 (25-220) | 光武→献帝 | 刘秀、班超、马援、张衡、蔡伦、张角、董卓、袁绍 | 54 (AD 50) | ✅ |
| 三国 (220-280) | 曹魏/蜀汉/东吴 | 曹操、刘备、孙权、诸葛亮、关羽、周瑜、司马懿 | 89 (AD 220) | ✅ |
| 两晋 (266-420) | 西晋+东晋 | 司马炎、贾南风、王导、谢安、桓温 | 46 (AD 400) | ✅ |
| 南北朝 (420-589) | 宋齐梁陈+北朝 | 刘裕、萧衍、侯景、陈霸先、拓跋珪、孝文帝、高欢、宇文泰 | 290 (AD 550) | ✅ |
| 隋 (581-618) | 杨坚→杨广 | 杨坚、独孤伽罗、杨广、李密、窦建德、王世充 | 233 (AD 600) | ✅ |
| 唐 (618-907) | 高祖→哀帝 | 李渊、李世民、武则天、玄宗、李白、杜甫、安禄山、郭子仪、李德裕、黄巢、朱温 | 871 (AD 700/800/900) | ✅ |
| 五代十国 (907-979) | 5代14帝+10国 | 朱温、李克用、李存勖、石敬瑭、柴荣、赵匡胤、十国君主 | 292 (AD 947) | ✅ |
| 北宋 (960-1127) | 太祖→钦宗 | 赵匡胤、范仲淹、王安石、苏轼、司马光 | 295 (AD 1050/1100) | ✅ |
| 南宋 (1127-1279) | 高宗→末帝 | 赵构、岳飞、秦桧、朱熹、陆游、文天祥 | 240 (AD 1200) | ✅ |
| 辽 (916-1125) | 契丹/辽 | 耶律阿保机、耶律德光、萧太后 | 285 | ✅ |
| 西夏 (1038-1227) | 党项 | 李继迁、李元昊 | (CHGIS 未单独提供,文献不足) | ⚠️ |
| 金 (1115-1234) | 女真 | 完颜阿骨打、完颜宗弼、完颜亮、完颜雍 | (合并在北宋/南宋) | ✅ |
| 元 (1206-1368) | 蒙古/元 | 成吉思汗、忽必烈、耶律楚材、脱脱、朱元璋(元末) | 256 (AD 1300) | ✅ |
| 明 (1368-1644) | 太祖→思宗 | 朱元璋、朱棣、王阳明、张居正、戚继光、海瑞 | 254 (AD 1400/1500) | ✅ |
| 清 (1636-1912) | 太祖→逊帝 | 努尔哈赤、康熙、雍正、乾隆、林则徐、曾国藩、李鸿章、慈禧 | 269 (AD 1700/1800/1900) | ✅ |

✅ **22/22 时间切片测试通过(BC 218 → AD 1900,0 空白年代,共 6,444 个多边形)**

---

## Final statistics

| 类别 | 数量 |
|---|---|
| **Person 人物** | 5,311 (419 种子 + 4,892 CBDB) |
| **Polity 政权** | 55 |
| **Event 事件** | 122 |
| **Battle 战役** | 34 |
| **Faction 派系** | 28 |
| **Place 地点** | 1,453 (448 种子 + 1,005 CBDB 地址) |
| **Dynasty 大朝代** | 8 |
| **总实体** | **7,011** |
| **关系** | **9,909** |
| **疆域 GeoJSON** | **34 个文件**(16 五代手工 + 18 CHGIS 朝代) |

---

## Verified cross-era queries (验证跨朝代查询)

### 关系密度(1 跳邻居数,CBDB 增强后)

| 人物 | 邻居数(增强前→后) |
|---|---|
| 朱熹 | ~5 → **749** |
| 苏轼 | ~5 → **393** |
| 王安石 | ~5 → **322** |
| 杜甫 | 0 → **258** |
| 李白 | 0 → **228** |
| 文天祥 | ~3 → **147** |
| 赵匡胤 | ~10 → **48** |

### 跨朝代最短路径

| 查询 | 路径 |
|---|---|
| 李白 → 朱熹 | **2 跳**(经 CBDB 中间人) |
| 武则天 → 王安石 | **5 跳**(经上官婉儿→李白→王安石文学圈) |
| 曹操 → 岳飞 | **6 跳**(经周瑜→朱熹→岳飞) |
| 赵匡胤 → 朱元璋 | **4 跳**(经宋→元朝代链) |
| 赵匡胤 → 朱熹 | **4 跳**(赵光义→岳飞→朱熹) |

### 时间切片

| 年代 | 人物数 |
|---|---|
| 1000 AD | 19 人(寇准/范仲淹/李继迁/毕昇/方腊…) |
| 1840 AD | 14 人(林则徐/道光/咸丰/慈禧/洪秀全/李鸿章/曾国藩…) |

---

## Phase log

| 阶段 | 内容 | 实体 | 关系 |
|---|---|---|---|
| 0-8 | 五代十国 demo | 242 | 276 |
| 9 | 中晚唐(763-907) | +105 | +81 |
| 10 | 隋+唐前期(581-763) | +115 | +74 |
| 11 | 魏晋南北朝(220-589) | +157 | +90 |
| 12 | 秦汉(BC 221-220) | +147 | +104 |
| 13 | 两宋(960-1279) | +175 | +133 |
| 14 | 元明清(1206-1912) | +171 | +141 |
| 15 | **CBDB 种子扩展**:419 种子 + 1-2 跳亲属/社交 | **+5,901** | **+9,010** |
| 16 | **CHGIS V5 各朝代 GeoJSON**:18 朝代文件,6,444 多边形 | — | — |
| **合计** | **秦→清,2100+年,7,011 实体** | **7,011** | **9,909** |

---

## 数据管线(可重现)

```bash
# 全部数据可以从原始权威源重建。所有 transformer 在 backend/scripts/

# 1. (已存)种子数据 - 14 个 seed_*.py 脚本,产出 data/entities/ + data/relations/

# 2. CBDB 增强
cd /Users/rick/ZCodeProject/history-kb/external_data
# 下载 CBDB SQLite (~131MB zip → 550MB db)
curl -L -o latest.zip "https://huggingface.co/datasets/cbdb/cbdb-sqlite/resolve/main/latest.zip"
unzip latest.zip

cd /Users/rick/ZCodeProject/history-kb
python backend/scripts/import_cbdb.py
# 产出: data/entities/persons/p_cbdb_*.yaml (4,892)
#       data/entities/places/pl_cbdb_*.yaml (1,005)
#       data/relations/cbdb.yaml (9,031)

# 3. CHGIS 增强
cd external_data
# 下载 CHGIS V5 府级时间序列多边形 (24MB)
curl -sL "https://dataverse.harvard.edu/api/access/datafile/2691132" -o v5_time_pref_pgn_utf.zip
mkdir chgis_v5 && cd chgis_v5 && unzip ../v5_time_pref_pgn_utf.zip

cd /Users/rick/ZCodeProject/history-kb
python backend/scripts/import_chgis.py
# 产出: data/geo/chgis_*.geojson (18 个朝代)
#       13 个 polity YAML 自动 patch territory 字段
```

依赖:`akshare / pandas / pyyaml / jinja2 / efinance / yfinance / tushare / opencc-python-reimplemented / pyshp / pyproj`

---

## How to run (this environment)

```bash
# Backend
cd /Users/rick/ZCodeProject/history-kb/backend
source /Users/rick/ZCodeProject/.venv/bin/activate
export DATA_DIR=/Users/rick/ZCodeProject/history-kb/data
export SCHEMA_DIR=/Users/rick/ZCodeProject/history-kb/schema
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend
cd /Users/rick/ZCodeProject/history-kb/frontend
npm run dev   # → http://localhost:5173
```

## Verification commands

```bash
# Stats (7,011 entities / 9,909 relations)
curl http://127.0.0.1:8000/api/meta/stats

# Map timeline - 全朝代覆盖
curl "http://127.0.0.1:8000/api/territories?year=750"   # 唐:871 多边形
curl "http://127.0.0.1:8000/api/territories?year=1840"  # 清:269 多边形

# Cross-era graph (CBDB-enhanced)
curl "http://127.0.0.1:8000/api/graph/shortest?from=p_li_bai&to=p_zhuxi&max_depth=6"
curl "http://127.0.0.1:8000/api/graph/neighbors/p_zhuxi?depth=1"   # 749 邻居

# Smoke test
DATA_DIR=$(pwd)/../data SCHEMA_DIR=$(pwd)/../schema python tests/test_smoke.py
```

---

## Known limitations

1. **CBDB 种子匹配率 88%**(369/419)——少数特殊用字(胡亥、扶苏、玄奘)需手工修正后入库。
2. **CHGIS 西夏数据缺失**——CHGIS V5 因文献不足未单独提供西夏府级多边形。
3. **CHGIS 投影为 Gauss-Kruger**——已通过 pyproj 反投影到 WGS84。
4. **CBDB 关系仅含 1 跳**——为控制数据规模,未做 2 跳全展开。可按需在 transformer 中提升 depth。
5. **关系密度集中在文坛**——CBDB 中文学交往(赠诗/墓志铭/书序)占大头,这是中国古代士人网络的真实结构。
6. **所有数据 carries `sources` field** for research traceability, primarily 正史 + CBDB + CHGIS。

---

## Compliance note

本作品为个人研究/学习用途。所有数据均附史料出处,以正史(二十四史、资治通鉴、续资治通鉴长编等)为基础,辅以现代学术研究(陈寅恪、谷川道雄、毛汉光等)及结构化数据库(CBDB / CHGIS)。具体日期、人物关系可能存在史源差异,标注"约"或留空处请以正史为准。
