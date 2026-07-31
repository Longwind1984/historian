#!/usr/bin/env python3
"""Generate relations YAML for the Five Dynasties & Ten Kingdoms.

All relations carry since/until where applicable, enabling time-slice queries.
"""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"

# Each tuple: (from, to, type, since_year, since_month, until_year, until_month, note)
# year=None means unknown
RELATIONS = [
    # ============ 后梁 ============
    ("p_zhuwen", "p_zhuyougui", "father_of", 888, None, 912, 7, "第三子"),
    ("p_zhuwen", "p_zhuyouzhen", "father_of", 888, None, 912, 7, "第四子"),
    ("p_zhuyougui", "p_zhuwen", "killed", 912, 7, None, None, "弑父篡位"),
    ("p_zhuyouzhen", "p_zhuyougui", "killed", 913, 2, None, None, "诛友珪自立"),
    ("p_zhuwen", "k_houliang", "founded", 907, 4, None, None, "篡唐建梁"),
    ("p_zhuwen", "k_tang", "usurped", 907, 4, None, None, "唐哀帝禅让"),
    ("p_zhuwen", "pl_songzhou", "born_in", None, None, None, None, "籍贯"),
    ("p_zhuwen", "pl_kaifeng", "born_in", 907, 4, 912, 7, "定都"),
    ("k_houliang", "pl_kaifeng", "capital_at", 907, 4, 923, 11, None),
    ("k_houliang", "k_tang", "supplanted", 907, 4, None, None, "取代唐朝"),
    ("p_zhuyougui", "k_houliang", "succeeded_by", 912, 7, 913, 2, "郢王"),
    ("p_zhuyouzhen", "k_houliang", "succeeded_by", 913, 2, 923, 11, "末帝"),
    ("k_houliang", "k_houdong", "destroyed_by", 923, 11, None, None, "为后唐所灭"),
    ("p_zhuwen", "p_likaiqu", "rival_of", 884, None, 912, 7, "梁晋长期争霸"),
    ("p_zhuwen", "f_zhuwen_group", "leader_of", 880, None, 912, 7, None),

    # ============ 后唐 ============
    ("p_likaiqu", "p_licunxu", "father_of", 885, 12, 908, 1, None),
    ("p_licunxu", "p_lisiyuan", "served_under", 913, None, 926, 5, "庄宗养子关系;后为明宗"),
    ("p_likaiqu", "k_houdong", "founded", 923, 4, None, None, "灭梁建唐(子存勖完成)"),
    ("p_likaiqu", "f_shatuo", "leader_of", 880, None, 908, 1, None),
    ("p_licunxu", "f_shatuo", "leader_of", 908, 1, 926, 5, None),
    ("p_licunxu", "k_houdong", "founded", 923, 4, None, None, "庄宗灭梁即位"),
    ("p_licunxu", "p_guocongqian", "served_under", 923, None, 926, 5, "伶人"),
    ("p_guocongqian", "p_licunxu", "killed", 926, 5, None, None, "兴教门之变"),
    ("p_lisiyuan", "k_houdong", "succeeded_by", 926, 5, 933, 12, "明宗"),
    ("p_liconghou", "k_houdong", "succeeded_by", 933, 12, 934, 4, "闵帝"),
    ("p_licongke", "k_houdong", "succeeded_by", 934, 4, 936, 11, "末帝"),
    ("p_licongke", "p_liconghou", "usurped", 934, 4, None, None, "废闵帝"),
    ("k_houdong", "pl_luoyang", "capital_at", 923, 4, 936, 11, None),
    ("k_houdong", "k_houjin", "destroyed_by", 936, 11, None, None, "石敬瑭借契丹兵所灭"),
    ("p_licongke", "p_shijingtan", "rival_of", 936, 1, 936, 11, "末帝 vs 石敬瑭"),
    ("p_lisiyuan", "p_shijingtan", "father_of", None, None, None, None, "翁婿(实为养女之夫)"),
    ("p_lisiyuan", "f_shatuo", "leader_of", 926, 5, 933, 12, None),

    # ============ 后晋 ============
    ("p_shijingtan", "p_lisiyuan", "served_under", None, None, 936, 11, "李嗣源女婿"),
    ("p_shijingtan", "k_houjin", "founded", 936, 11, None, None, "借契丹兵灭唐建晋"),
    ("p_shijingtan", "p_yeludeguang", "served_under", 936, 11, 942, 6, "儿皇帝,称臣于契丹"),
    ("p_shijingtan", "k_liao", "served_under", 936, 11, 942, 6, "自称儿皇帝"),
    ("p_shijingtan", "k_houdong", "usurped", 936, 11, None, None, "灭后唐"),
    ("p_shijingtan", "p_shizhonggui", "uncle_of", None, None, None, None, "叔侄(石敬瑭兄子)"),
    ("p_shizhonggui", "k_houjin", "succeeded_by", 942, 6, 947, 1, "出帝"),
    ("p_shizhonggui", "k_liao", "rival_of", 944, None, 947, 1, "称孙不称臣,引发战争"),
    ("p_yeludeguang", "p_shizhonggui", "killed", 947, 1, None, None, "俘出帝于汴梁"),
    ("k_houjin", "pl_kaifeng", "capital_at", 937, 3, 947, 1, None),
    ("k_houjin", "k_liao", "destroyed_by", 947, 1, None, None, "为契丹所灭"),
    ("p_shijingtan", "f_shatuo", "member_of", None, None, None, None, None),

    # ============ 后汉 ============
    ("p_liuzhiyuan", "p_shijingtan", "served_under", None, None, 942, 6, "后晋重臣"),
    ("p_liuzhiyuan", "k_houhan", "founded", 947, 2, None, None, "契丹北撤后建国"),
    ("p_liuchengyou", "k_houhan", "succeeded_by", 948, 1, 950, 12, "隐帝"),
    ("p_liuzhiyuan", "p_liuchengyou", "father_of", 931, None, None, None, None),
    ("p_liuchengyou", "p_guowei", "rival_of", 950, 11, 950, 12, "欲杀郭威失败"),
    ("p_liuchengyou", "p_guowei", "killed", 950, 12, None, None, "郭威家属被诛,反激起兵变"),
    ("k_houhan", "pl_kaifeng", "capital_at", 947, 2, 950, 12, None),
    ("k_houhan", "k_houzhou", "destroyed_by", 950, 12, None, None, "郭威兵变"),
    ("p_liuzhiyuan", "p_liuchong", "sibling_of", None, None, None, None, "兄弟"),
    ("p_liuzhiyuan", "f_shatuo", "member_of", None, None, None, None, None),

    # ============ 后周 ============
    ("p_guowei", "k_houzhou", "founded", 951, 1, None, None, "代汉建周"),
    ("p_guowei", "k_houhan", "usurped", 950, 12, None, None, None),
    ("p_guowei", "p_chairong", "father_of", None, None, 954, 2, "养子(柴氏子,从柴姓)"),
    ("p_chairong", "k_houzhou", "succeeded_by", 954, 2, 959, 7, "世宗"),
    ("p_chairong", "p_chaizongxun", "father_of", 953, 9, None, None, None),
    ("p_chaizongxun", "k_houzhou", "succeeded_by", 959, 7, 960, 2, "恭帝,7岁即位"),
    ("p_zhaokuangyin", "p_chaizongxun", "usurped", 960, 2, None, None, "陈桥兵变"),
    ("p_zhaokuangyin", "k_song", "founded", 960, 2, None, None, "代周建宋"),
    ("p_zhaokuangyin", "p_chairong", "served_under", 954, None, 959, 7, "殿前都点检"),
    ("k_houzhou", "pl_kaifeng", "capital_at", 951, 1, 960, 2, None),
    ("k_houzhou", "k_song", "destroyed_by", 960, 2, None, None, "陈桥兵变"),
    ("p_chairong", "p_liuchong", "rival_of", 954, 3, 959, 7, "高平之战"),
    ("p_chairong", "b_gaoping", "led", 954, 3, None, None, "亲自督战"),
    ("p_chairong", "b_houzhou_nantang", "led", 956, 2, None, None, "三征南唐"),
    ("p_chairong", "b_houzhou_liao", "led", 959, 4, None, None, "北伐辽"),
    ("p_chairong", "e_zhou_reform", "participated_in", 955, None, 959, 7, "主导"),
    ("p_chairong", "e_zhou_buddhism", "participated_in", 955, None, None, None, "主导灭佛"),

    # ============ 北宋 ============
    ("p_zhaokuangyin", "p_chairong", "served_under", 954, None, 959, 7, None),
    ("p_zhaokuangyin", "b_song_jingnan", "led", 963, 1, None, None, "策动"),
    ("p_zhaokuangyin", "b_song_houshu", "led", 964, 11, None, None, "策动"),
    ("p_zhaokuangyin", "b_song_nanhan", "led", 970, 9, None, None, "策动"),
    ("p_zhaokuangyin", "b_song_nantang", "led", 974, 9, None, None, "策动"),
    ("k_song", "pl_kaifeng", "capital_at", 960, 2, None, None, None),

    # ============ 前蜀 ============
    ("p_wangjian", "k_qianshu", "founded", 907, 9, None, None, None),
    ("p_wangyan", "k_qianshu", "succeeded_by", 918, 6, 925, 11, "后主"),
    ("p_wangjian", "p_wangyan", "father_of", 899, None, None, None, "第十一子"),
    ("k_qianshu", "pl_chengdu", "capital_at", 907, 9, 925, 11, None),
    ("k_qianshu", "k_houdong", "destroyed_by", 925, 11, None, None, "郭崇韬统兵灭之"),
    ("p_licunxu", "b_qianshu_conquest", "led", 925, 9, None, None, "遣郭崇韬") if False else None,
    ("p_guoweiwei", "k_qianshu", "destroyed_by", 925, 11, None, None, "925年统兵灭前蜀"),

    # ============ 后蜀 ============
    ("p_mengzhixiang", "k_houshu", "founded", 934, 1, None, None, None),
    ("p_mengchang", "k_houshu", "succeeded_by", 934, 8, 965, 2, "后主"),
    ("p_mengzhixiang", "p_mengchang", "father_of", 919, None, None, None, None),
    ("k_houshu", "pl_chengdu", "capital_at", 934, 1, 965, 2, None),
    ("k_houshu", "k_song", "destroyed_by", 965, 2, None, None, None),

    # ============ 杨吴 + 南唐 ============
    ("p_yanghangmi", "k_yangwu", "founded", 902, 4, None, None, "唐封吴王"),
    ("p_yangpu", "k_yangwu", "succeeded_by", 920, None, 937, 10, "睿帝"),
    ("k_yangwu", "pl_jinling", "capital_at", 937, None, 937, 10, "迁都金陵(杨溥时)"),
    ("p_xuzhigao", "k_nantang", "founded", 937, 10, None, None, "代吴建齐→唐"),
    ("p_libian", "k_nantang", "founded", 937, 10, None, None, "李昪(同徐知诰)"),
    ("p_lijing", "k_nantang", "succeeded_by", 943, 3, 961, 8, "元宗"),
    ("p_liyu", "k_nantang", "succeeded_by", 961, 8, 975, 11, "后主"),
    ("p_libian", "p_lijing", "father_of", 916, None, None, None, None),
    ("p_lijing", "p_liyu", "father_of", 937, 7, None, None, "第六子"),
    ("p_xuzhigao", "p_libian", "sibling_of", None, None, None, None, "同一人(改名)"),
    ("k_nantang", "pl_jinling", "capital_at", 937, 10, 975, 11, None),
    ("k_nantang", "k_min", "destroyed_by", 945, 11, None, None, "灭闽"),
    ("k_nantang", "k_chu", "destroyed_by", 951, 11, None, None, "灭楚"),
    ("k_nantang", "k_song", "destroyed_by", 975, 11, None, None, "宋灭南唐"),
    ("p_lijing", "f_nantang_faction", "member_of", 943, None, 961, 8, None),
    ("p_liyu", "f_nantang_faction", "member_of", 961, None, 975, 11, None),
    ("p_liyu", "b_song_nantang", "participated_in", 974, 9, 976, 1, "被围金陵"),

    # ============ 吴越 ============
    ("p_qianliu", "k_wuyue", "founded", 907, 5, None, None, "后梁封吴越王"),
    ("p_qianyuanguan", "k_wuyue", "succeeded_by", 932, 3, 941, 9, "文穆王"),
    ("p_qianhongzuo", "k_wuyue", "succeeded_by", 941, 9, 947, 6, "忠献王"),
    ("p_qianhongchu", "k_wuyue", "succeeded_by", 948, 8, 978, 5, "忠懿王"),
    ("p_qianliu", "p_qianyuanguan", "father_of", 887, None, None, None, "第七子"),
    ("p_qianyuanguan", "p_qianhongzuo", "father_of", 928, None, None, None, None),
    ("p_qianyuanguan", "p_qianhongchu", "father_of", 929, 8, None, None, "第九子"),
    ("p_qianliu", "f_qian_group", "leader_of", 875, None, 932, 3, None),
    ("k_wuyue", "pl_hangzhou", "capital_at", 907, 5, 978, 5, None),
    ("k_wuyue", "k_song", "destroyed_by", 978, 5, None, None, "纳土归宋"),
    ("p_qianhongchu", "e_jingnan_peace", "participated_in", 978, 5, None, None, "纳土归宋"),
    ("p_qianhongchu", "k_song", "served_under", 978, 5, None, None, "归宋"),

    # ============ 闽 ============
    ("p_wangshenzhi", "k_min", "founded", 909, 4, None, None, "后梁封闽王"),
    ("p_wangyanjun", "k_min", "succeeded_by", 927, None, 935, 10, "太宗"),
    ("p_wangyanxi", "k_min", "succeeded_by", 939, None, 944, 3, "景宗"),
    ("p_wangshenzhi", "p_wangyanjun", "father_of", None, None, None, None, "次子"),
    ("p_wangshenzhi", "p_wangyanxi", "father_of", None, None, None, None, None),
    ("k_min", "pl_fuzhou", "capital_at", 909, 4, 945, 11, None),
    ("k_min", "k_nantang", "destroyed_by", 945, 11, None, None, None),

    # ============ 楚 ============
    ("p_mayin", "k_chu", "founded", 907, 4, None, None, "后梁封楚王"),
    ("p_maxifan", "k_chu", "succeeded_by", 930, None, 947, 5, "文昭王"),
    ("p_mayin", "p_maxifan", "father_of", 899, None, None, None, "次子"),
    ("k_chu", "pl_changsha", "capital_at", 907, 4, 951, 11, None),
    ("k_chu", "k_nantang", "destroyed_by", 951, 11, None, None, None),

    # ============ 南汉 ============
    ("p_liuyan", "k_nanhan", "founded", 917, 8, None, None, "称帝于广州"),
    ("p_liuchang", "k_nanhan", "succeeded_by", 958, None, 971, 3, "后主"),
    ("p_liuyan", "p_liuchang", "grandfather_of", None, None, None, None, None),
    ("k_nanhan", "pl_guangzhou", "capital_at", 917, 8, 971, 3, None),
    ("k_nanhan", "k_song", "destroyed_by", 971, 3, None, None, None),
    ("p_liuchang", "b_song_nanhan", "participated_in", 970, 9, 971, 2, "败降"),

    # ============ 荆南/南平 ============
    ("p_gaojixing", "k_jingnan", "founded", 924, 3, None, None, "后唐封南平王"),
    ("p_gaobaorong", "k_jingnan", "succeeded_by", 948, None, 960, 8, "贞懿王"),
    ("k_jingnan", "pl_jiangling", "capital_at", 924, 3, 963, 3, None),
    ("k_jingnan", "k_song", "destroyed_by", 963, 3, None, None, None),

    # ============ 北汉 ============
    ("p_liuchong", "k_beihan", "founded", 951, 2, None, None, "后周代汉,刘崇据太原称帝"),
    ("p_liuchong", "k_liao", "served_under", 951, 2, 954, 11, "称侄于契丹"),
    ("p_liuchong", "b_gaoping", "led", 954, 3, None, None, "联合契丹南下"),
    ("p_liujiyuan", "k_beihan", "succeeded_by", 968, None, 979, 6, "末代君主"),
    ("p_liuchong", "p_liujiyuan", "grandfather_of", None, None, None, None, None),
    ("k_beihan", "pl_taiyuan", "capital_at", 951, 2, 979, 6, None),
    ("k_beihan", "k_song", "destroyed_by", 979, 6, None, None, "宋太宗亲征"),
    ("p_liujiyuan", "b_song_beihan", "participated_in", 979, 2, 979, 6, "坚守至粮尽降"),

    # ============ 契丹/辽 ============
    ("p_yeluabaoji", "k_liao", "founded", 916, 1, None, None, None),
    ("p_yeludeguang", "k_liao", "succeeded_by", 926, 11, 947, 5, "辽太宗"),
    ("p_yeluabaoji", "p_yeludeguang", "father_of", 902, None, None, None, "次子"),
    ("k_liao", "pl_liaoshangjing", "capital_at", 916, 1, None, None, None),
    ("p_yeludeguang", "b_yanzhou_liao", "led", 946, 12, None, None, "亲征灭晋"),
    ("p_yeludeguang", "e_liao_kingdom", "participated_in", 947, None, None, None, "改国号辽"),
    ("p_yeludeguang", "k_houjin", "destroyed_by", 947, 1, None, None, None),

    # ============ 关陇集团 ============
    ("p_yuwentai", "f_guanlong", "leader_of", 530, None, 556, None, "创立者"),
    ("p_yangjian", "f_guanlong", "member_of", 541, 7, 604, 8, None),
    ("p_yuwentai", "p_yangjian", "predecessor_of", None, None, None, None, "杨坚承袭关陇政治遗产"),
    ("p_yangjian", "pl_wuyang", "born_in", None, None, None, None, None),
    ("p_yuwentai", "pl_wuchuan", "born_in", None, None, None, None, None),

    # ============ 五代乱世文人 ============
    ("p_fengdao", "f_literati_5d", "leader_of", 900, None, 954, 4, "历仕四朝十帝"),
    ("p_fengdao", "k_houliang", "served_under", 910, None, 923, 11, None),
    ("p_fengdao", "k_houdong", "served_under", 923, 11, 936, 11, None),
    ("p_fengdao", "k_houjin", "served_under", 936, 11, 947, 1, None),
    ("p_fengdao", "k_liao", "served_under", 947, 1, 947, 4, "事契丹辽太宗"),
    ("p_fengdao", "k_houhan", "served_under", 947, 4, 950, 12, None),
    ("p_fengdao", "k_houzhou", "served_under", 951, 1, 954, 4, None),

    # ============ 跨派系 ============
    ("f_shatuo", "f_heshuo", "rival_of", 880, None, 929, None, "沙陀集团崛起过程中兼并河朔"),
    ("f_shatuo", "f_zhuwen_group", "rival_of", 880, None, 923, 11, "晋梁争霸"),
    ("f_zhuwen_group", "f_heshuo", "rival_of", 880, None, 923, None, None),
    ("f_khitan", "f_shatuo", "rival_of", 916, None, 979, None, "契丹 vs 沙陀集团"),

    # ============ Polity 链 ============
    ("k_houliang", "k_houdong", "succeeded_by", 923, 11, None, None, "灭梁"),
    ("k_houdong", "k_houjin", "succeeded_by", 936, 11, None, None, "灭唐"),
    ("k_houjin", "k_houhan", "succeeded_by", 947, 2, None, None, "晋亡后汉立"),
    ("k_houhan", "k_houzhou", "succeeded_by", 950, 12, None, None, "郭威兵变"),
    ("k_houzhou", "k_song", "succeeded_by", 960, 2, None, None, "陈桥兵变"),
]


def to_dict(rel):
    f, t, type_, sy, sm, uy, um, note = rel
    obj = {"from": f, "to": t, "type": type_}
    if sy is not None:
        d = {"year": sy}
        if sm is not None:
            d["month"] = sm
        obj["since"] = d
    if uy is not None:
        d = {"year": uy}
        if um is not None:
            d["month"] = um
        obj["until"] = d
    if note:
        obj["note"] = note
    return obj


def gen_relations():
    items = [to_dict(r) for r in RELATIONS if r is not None]
    # dedupe by (from,to,type)
    seen = set()
    deduped = []
    for r in items:
        key = (r["from"], r["to"], r["type"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    out = DATA / "relations" / "all.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        yaml.safe_dump(deduped, f, allow_unicode=True, sort_keys=False)
    print(f"  ✓ {len(deduped)} relations → data/relations/all.yaml")


if __name__ == "__main__":
    print(f"→ generating relations")
    gen_relations()
