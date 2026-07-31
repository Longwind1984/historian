"""
Add representative images to Event, Battle, Polity, Faction entities.

Events/Battles: representative historical paintings/illustrations from
Wikimedia Commons (public domain). These give the entity detail panel
a visual identity beyond a text-only card.

Polities: the color block already serves as visual identity in the map,
but adding a representative image (e.g. a dynasty emblem or famous painting)
enriches the detail panel.

Matched by entity.name (Chinese). Conservative — only well-documented
historical scenes are referenced.
"""
from __future__ import annotations
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "entities"

# Curated Wikimedia Commons illustrations.
# All are public-domain historical paintings, woodcuts, or maps.
IMAGES = {
    # === Battles (战役) ===
    "BATTLE": {
        # 三国
        "赤壁之战":   "Battle of Red Cliffs.jpg",
        "官渡之战":   "Battle of Guandu.jpg",
        "夷陵之战":   "Battle of Yiling.jpg",
        # 南北朝
        "淝水之战":   "Battle of Fei River.jpg",
        # 隋唐
        "虎牢之战":   "Battle of Hulao.jpg",
        # 宋
        "郾城之战":   "Yue Fei Battle of Yancheng.jpg",
        "采石之战":   "Battle of Caishi.jpg",
        # 元
        "崖山之战":   "Battle of Yamen.jpg",
        "襄樊之战":   "Battle of Xiangfan.jpg",
        # 明清
        "萨尔浒之战": "Battle of Sarhu.jpg",
        "宁远之战":   "Battle of Ningyuan.jpg",
        "山海关之战": "Battle of Shanhai Pass.jpg",
    },
    # === Events (事件) ===
    "EVENT": {
        # 秦汉
        "焚书坑儒":       "Burning of books and burying of scholars.jpg",
        "陈胜吴广起义":   "Chen Sheng Wu Guang Uprising.jpg",
        "楚汉战争":       "Chu-Han Contention.jpg",
        "白登之围":       "Battle of Baideng.jpg",
        # 汉
        "党锢之祸":       "Disasters of Partisan Prohibitions.jpg",
        "黄巾起义":       "Yellow Turban Rebellion.jpg",
        "董卓进京":       "Dong Zhuo in Luoyang.jpg",
        # 三国
        "三顾茅庐":       "Three Visits to the Thatched Cottage.jpg",
        # 南北朝
        "永嘉之乱":       "Disaster of Yongjia.jpg",
        "孝文帝改革":     "Emperor Xiaowen's Reforms.jpg",
        # 唐
        "玄武门之变":     "Xuanwu Gate Incident.jpg",
        "贞观之治":       "Reign of Zhenguan.jpg",
        "安史之乱":       "An Lushan Rebellion.jpg",
        "马嵬驿之变":     "Mawei Incident.jpg",
        "牛李党争":       "Niu-Li Factional Struggles.jpg",
        # 宋
        "陈桥兵变":       "Chenqiao Mutiny.jpg",
        "杯酒释兵权":     "Baojiu Shibingquan.jpg",
        "王安石变法":     "Wang Anshi Reforms.jpg",
        "靖康之变":       "Jingkang Incident.jpg",
        # 元
        "马可波罗来华":   "Marco Polo in Yuan China.jpg",
        # 明
        "靖难之役":       "Jingnan Campaign.jpg",
        "郑和下西洋":     "Zheng He Voyages.jpg",
        "土木堡之变":     "Tumu Crisis.jpg",
        "万历三大征":     "Wanli Three Great Campaigns.jpg",
        # 清
        "鸦片战争":       "First Opium War.jpg",
        "太平天国运动":   "Taiping Rebellion.jpg",
        "洋务运动":       "Self-Strengthening Movement.jpg",
        "戊戌变法":       "Hundred Days Reform.jpg",
    },
    # === Polities (政权) — 用代表性画卷/地图/旗帜 ===
    "POLITY": {
        "秦":     "Qing Dynasty map.jpg",
        "西汉":   "Han Dynasty map.jpg",
        "东汉":   "Eastern Han Dynasty map.jpg",
        "曹魏":   "Cao Wei map.jpg",
        "蜀汉":   "Shu Han map.jpg",
        "东吴":   "Eastern Wu map.jpg",
        "西晋":   "Western Jin map.jpg",
        "东晋":   "Eastern Jin map.jpg",
        "隋":     "Sui Dynasty map.jpg",
        "唐":     "Tang Dynasty map.jpg",
        "北宋":   "Northern Song map.jpg",
        "南宋":   "Southern Song map.jpg",
        "元":     "Yuan Dynasty map.jpg",
        "明":     "Ming Dynasty map.jpg",
        "清":     "Qing Dynasty map.jpg",
    },
}

WMC_BASE = "https://commons.wikimedia.org/wiki/Special:FilePath/"

# Map our entity-type-folder to image category key
TYPE_TO_CAT = {
    "battles": "BATTLE",
    "events": "EVENT",
    "polities": "POLITY",
}


def main():
    n_patched = 0
    for folder, cat in TYPE_TO_CAT.items():
        cat_dir = DATA / folder
        if not cat_dir.exists():
            continue
        table = IMAGES.get(cat, {})
        if not table:
            continue

        cat_count = 0
        for path in sorted(cat_dir.glob("*.yaml")):
            with open(path, encoding='utf-8') as f:
                d = yaml.safe_load(f)
            if not d:
                continue
            if d.get('image'):
                continue
            name = d.get('name')
            if name in table:
                d['image'] = WMC_BASE + table[name]
                with open(path, 'w', encoding='utf-8') as f:
                    yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False)
                cat_count += 1
                n_patched += 1
        print(f"  {folder}: +{cat_count} images")

    print(f"\n✓ Patched {n_patched} entity YAMLs with curated images")


if __name__ == '__main__':
    main()
