"""
Generate avatar URLs for entities.

Strategy:
  - For ~80 most famous persons, hardcode Wikimedia Commons file paths
    (public-domain historical portraits).
  - For all others, return None and let the frontend render an SVG data URL
    (initials/dynasty color).

This script patches Person YAML files to add `image:` field where we
have a confident Wikimedia match. Matched by Person.name (not file name).

Output: data/entities/persons/<id>.yaml gets image: <url>
"""
from __future__ import annotations
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PERSONS_DIR = ROOT / "data" / "entities" / "persons"

# Curated Wikimedia Commons portraits (public-domain / cc-by-sa).
# Matched by Chinese name (more reliable than file slug).
CURATED_PORTRAITS = {
    # 秦汉
    "秦始皇":   "Qinshihuang.jpg",
    "刘邦":     "Gaozu_han.jpg",
    "汉武帝":   "Emperor Wu of Han 2.jpg",
    "刘彻":     "Emperor Wu of Han 2.jpg",
    "王莽":     "Wang Mang.jpg",
    "刘秀":     "Emperor Guangwu of Han.jpg",
    "班超":     "Ban Chao.jpg",
    "张衡":     "Zhang Heng.jpg",
    "蔡伦":     "Cai Lun (cropped).jpg",
    # 三国
    "曹操":     "Cao Cao in Sancai Tuhui.jpg",
    "刘备":     "Liu Bei in Sancai Tuhui.jpg",
    "孙权":     "Sun Quan in Sancai Tuhui.jpg",
    "诸葛亮":   "Zhuge Liang in Sancai Tuhui.jpg",
    "关羽":     "Guan Yu in Sancai Tuhui.jpg",
    "司马懿":   "Sima Yi in Sancai Tuhui.jpg",
    "周瑜":     "Zhou Yu in Sancai Tuhui.jpg",
    # 晋南北朝
    "司马炎":   "Emperor Wu of Jin.jpg",
    "谢安":     "Xie An.jpg",
    "拓跋宏":   "Emperor Xiaowen of Northern Wei.jpg",
    # 隋唐
    "杨坚":     "Emperor Wen of Sui.jpg",
    "杨广":     "Emperor Yang of Sui.jpg",
    "李渊":     "Emperor Gaozu of Tang.jpg",
    "李世民":   "TangTaizong.jpg",
    "武曌":     "Wu Zetian2.jpg",
    "武则天":   "Wu Zetian2.jpg",
    "玄奘":     "Xuanzang portrait.jpg",
    "李白":     "Li Bai 701 - 762.jpg",
    "杜甫":     "Tu Fu.jpg",
    "白居易":   "Bai Juyi 2.jpg",
    "韩愈":     "Han Yu.jpg",
    "柳宗元":   "Liu Zongyuan.jpg",
    "安禄山":   "An Lushan.jpg",
    "郭子仪":   "Guo Ziyi.jpg",
    "颜真卿":   "Yan Zhenqing.jpg",
    # 五代宋
    "赵匡胤":   "Song Taizu 1.jpg",
    "范仲淹":   "Fan Zhongyan.jpg",
    "王安石":   "Wang Anshi 4.jpg",
    "司马光":   "Sima Guang.jpg",
    "苏轼":     "Su Shi 1057-1101.jpg",
    "欧阳修":   "Ouyang Xiu.jpg",
    "岳飞":     "Yue Fei.jpg",
    "朱熹":     "Zhu Xi.jpg",
    "陆游":     "Lu You.jpg",
    "文天祥":   "Wen Tianxiang.jpg",
    "辛弃疾":   "Xin Qiji.jpg",
    "李清照":   "Li Qingzhao en.svg",
    # 辽金元
    "成吉思汗": "Genghis Khan portrait.jpg",
    "铁木真":   "Genghis Khan portrait.jpg",
    "忽必烈":   "YuanShizu.jpg",
    "耶律楚材": "Yelü Chucai.jpeg",
    # 明清
    "朱元璋":   "Hongwu1.jpg",
    "朱棣":     "Yongling-Oil-Yongle.jpg",
    "王守仁":   "Wang Yangming.jpg",
    "王阳明":   "Wang Yangming.jpg",
    "张居正":   "Zhang Juzheng.jpg",
    "戚继光":   "Qi Jiguang.jpg",
    "海瑞":     "Hai Rui.jpg",
    "李自成":   "Li Zicheng.jpg",
    "郑成功":   "Koxinga 2.jpg",
    "康熙":     "Kangxi Emperor-Full Portrait-Frontface.jpg",
    "玄烨":     "Kangxi Emperor-Full Portrait-Frontface.jpg",
    "雍正":     "Yongzheng Emperor.jpg",
    "胤禛":     "Yongzheng Emperor.jpg",
    "乾隆":     "Portrait of Qianlong Emperor.jpg",
    "弘历":     "Portrait of Qianlong Emperor.jpg",
    "林则徐":   "Lin Zexu 1839.jpg",
    "曾国藩":   "Zeng Guofan.jpg",
    "李鸿章":   "Li Hongzhang (cropped).jpg",
    "左宗棠":   "Zuo Zongtang 2.jpg",
    "洪秀全":   "Hong Xiuquan.jpg",
    "慈禧":     "Empress Dowager Cixi portrait.png",
    # 高僧/画家
    "鉴真":     "Jianzhen.jpg",
    "吴道子":   "Wu Daozi.jpg",
    "顾恺之":   "Gu Kaizhi 2.jpg",
}

WMC_BASE = "https://commons.wikimedia.org/wiki/Special:FilePath/"


def main():
    n_patched = 0
    n_skipped = 0
    n_no_match = 0

    for path in sorted(PERSONS_DIR.glob("*.yaml")):
        with open(path, encoding='utf-8') as f:
            d = yaml.safe_load(f)
        if not d or d.get('type') != 'Person':
            continue
        if d.get('image'):
            n_skipped += 1
            continue
        name = d.get('name')
        if name in CURATED_PORTRAITS:
            d['image'] = WMC_BASE + CURATED_PORTRAITS[name]
            with open(path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False)
            n_patched += 1
        else:
            n_no_match += 1

    print(f"✓ Patched {n_patched} Person YAMLs with curated Wikimedia portraits")
    print(f"  {n_skipped} already had image, {n_no_match} no curated match (will use generated avatar)")


if __name__ == '__main__':
    main()
