#!/usr/bin/env python3
"""Generate core YAML data for the Five Dynasties & Ten Kingdoms demo.

This is the authoritative generation script for the seed dataset.
Run it once to populate data/entities/* and data/relations/.

Usage:
    python backend/scripts/seed_data.py

After Agent research returns, augment with cross-checked additions
in separate YAML files (don't edit this script for those).
"""
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)


# ============================================================
# PLACES — 古今对照 + 经纬度
# ============================================================
PLACES = [
    # Capitals
    ("pl_kaifeng", "汴梁", "开封", "河南", 34.80, 114.31, "capital", ["汴州", "大梁", "开封府", "东京"], "后梁/晋/汉/周/宋都城"),
    ("pl_luoyang", "洛阳", "洛阳", "河南", 34.62, 112.45, "capital", ["洛京", "西京", "河南府"], "后唐都城"),
    ("pl_taiyuan", "晋阳", "太原", "山西", 37.77, 112.55, "capital", ["太原府", "北都", "北京"], "李克用/李存勖基地,北汉都城"),
    ("pl_chengdu", "成都", "成都", "四川", 30.67, 104.07, "capital", ["益州", "蜀都"], "前蜀/后蜀都城"),
    ("pl_jinling", "金陵", "南京", "江苏", 32.04, 118.78, "capital", ["建康", "江宁", "建邺"], "杨吴/南唐都城"),
    ("pl_yangzhou", "扬州", "扬州", "江苏", 32.39, 119.42, "capital", ["广陵", "江都"], "杨吴旧都"),
    ("pl_guangzhou", "广州", "广州", "广东", 23.13, 113.27, "capital", ["南海", "兴王府"], "南汉都城"),
    ("pl_fuzhou", "福州", "福州", "福建", 26.08, 119.30, "capital", ["长乐"], "闽都城"),
    ("pl_changsha", "长沙", "长沙", "湖南", 28.23, 112.94, "capital", ["潭州"], "楚都城"),
    ("pl_jiangling", "江陵", "荆州", "湖北", 30.33, 112.24, "capital", ["荆州", "南平"], "荆南/南平都城"),
    ("pl_hangzhou", "杭州", "杭州", "浙江", 30.27, 120.16, "capital", ["西府", "钱塘"], "吴越都城"),
    # Strategic cities / battlefields
    ("pl_youzhou", "幽州", "北京", "北京", 39.91, 116.40, "garrison", ["范阳", "析津"], "北方军事重镇,燕云十六州核心"),
    ("pl_yunzhou", "云州", "大同", "山西", 40.08, 113.30, "garrison", ["云中"], "燕云十六州之一"),
    ("pl_weizhou", "魏州", "大名", "河北", 36.27, 115.16, "garrison", ["魏府", "兴唐"], "河朔重镇,后唐龙兴地"),
    ("pl_qinzhou", "秦州", "天水", "甘肃", 34.58, 105.72, "city", ["天水"], "关陇要地"),
    ("pl_chang_an", "长安", "西安", "陕西", 34.27, 108.95, "city", ["京兆府", "雍州"], "故唐都城,五代时衰落"),
    ("pl_lizhou", "潞州", "长治", "山西", 36.20, 113.12, "battlefield", ["上党"], "朱梁vs晋 长期争夺"),
    ("pl_boxiang", "柏乡", "柏乡", "河北", 37.48, 114.68, "battlefield", [], "910 柏乡之战"),
    ("pl_yuncheng", "郓州", "东平", "山东", 35.91, 116.30, "garrison", ["天平"], "后唐灭梁突破点"),
    ("pl_shouzhou", "寿州", "寿县", "安徽", 32.57, 116.78, "battlefield", [], "后周攻南唐关键战场"),
    ("pl_gaoping", "高平", "高平", "山西", 35.80, 112.92, "battlefield", [], "954 高平之战"),
    ("pl_qizhou", "齐州", "济南", "山东", 36.65, 117.00, "city", ["济南"], "山东要地"),
    ("pl_zhenzhou", "镇州", "正定", "河北", 38.15, 114.57, "garrison", ["成德"], "河朔三镇之一"),
    ("pl_qingzhou", "青州", "青州", "山东", 36.68, 118.48, "garrison", ["平卢"], "平卢节度使治"),
    ("pl_xiazhou", "夏州", "靖边", "陕西", 37.60, 108.79, "garrison", ["统万"], "党项根据地"),
    # 燕云十六州
    ("pl_jizhou_yy", "蓟州", "蓟县", "天津", 40.05, 117.41, "garrison", [], "燕云十六州之一"),
    ("pl_yingzhou_yy", "瀛州", "河间", "河北", 38.45, 116.10, "garrison", [], "燕云十六州之一"),
    ("pl_mozhou_yy", "莫州", "任丘", "河北", 38.70, 116.10, "garrison", [], "燕云十六州之一"),
    ("pl_zhuozhou_yy", "涿州", "涿州", "河北", 39.49, 115.98, "garrison", [], "燕云十六州之一"),
    ("pl_tanzhou_yy", "檀州", "密云", "北京", 40.38, 116.84, "garrison", [], "燕云十六州之一"),
    ("pl_shunzhou_yy", "顺州", "顺义", "北京", 40.13, 116.65, "garrison", [], "燕云十六州之一"),
    ("pl_xinzhou_yy", "新州", "涿鹿", "河北", 40.38, 115.22, "garrison", [], "燕云十六州之一"),
    ("pl_guizhou_yy", "妫州", "怀来", "河北", 40.40, 115.55, "garrison", [], "燕云十六州之一"),
    ("pl_ruzhou_yy", "儒州", "延庆", "北京", 40.46, 115.97, "garrison", [], "燕云十六州之一"),
    ("pl_wuzhou_yy", "武州", "宣化", "河北", 40.61, 115.26, "garrison", [], "燕云十六州之一"),
    ("pl_yingzhou_yy2", "应州", "应县", "山西", 39.55, 113.19, "garrison", [], "燕云十六州之一"),
    ("pl_huanzhou_yy", "寰州", "朔州东", "山西", 39.40, 112.70, "garrison", [], "燕云十六州之一"),
    ("pl_shuozhou_yy", "朔州", "朔州", "山西", 39.33, 112.43, "garrison", [], "燕云十六州之一"),
    ("pl_weizhou_yy", "蔚州", "蔚县", "河北", 39.84, 114.59, "garrison", [], "燕云十六州之一"),
    # birthplaces
    ("pl_songzhou", "宋州", "商丘", "河南", 34.44, 115.65, "birthplace", ["睢阳"], "朱温籍贯"),
    ("pl_shenzhou_yanjiao", "神武川", "应县", "山西", 39.55, 113.19, "birthplace", [], "李克用籍贯(沙陀)"),
    # regions (concept)
    ("pl_hebei", "河北", "河北", "河北", 38.50, 115.50, "region", [], "广义地理区域"),
    ("pl_hedong", "河东", "山西", "山西", 37.50, 112.30, "region", [], "李克用/沙陀集团基地"),
    ("pl_jianghuai", "江淮", "江淮", "江苏安徽", 32.50, 118.50, "region", [], "杨吴/南唐核心区"),
    ("pl_guanzhong", "关中", "关中", "陕西", 34.30, 108.50, "region", [], "关陇集团故地"),
]

def gen_places():
    for tup in PLACES:
        pid, name, modern, prov, lat, lng, cat, aliases, desc = tup
        obj = {
            "id": pid, "type": "Place", "name": name,
            "modern_name": modern, "province": prov,
            "latitude": lat, "longitude": lng,
            "category": cat,
            "description": desc,
        }
        if aliases:
            obj["aliases"] = aliases
        obj["sources"] = ["旧五代史·郡县志", "新五代史·职方考", "中国历史地图集·隋唐五代十国"]
        write(DATA / "entities" / "places" / f"{pid[3:]}.yaml", obj)


# ============================================================
# POLITIES — 五代 + 十国
# ============================================================
POLITIES = [
    # 五代 (中原正统)
    ("k_houliang", "后梁", "Later Liang", "#c0392b", (907,4), (923,11), "p_zhuwen", "pl_kaifeng", None, "k_houdong",
     "五代之首。朱温(朱全忠)907 年篡唐所建,都开封(汴梁)。与河东李克用、李存勖父子长期对峙,923 年为后唐所灭。",
     "旧五代史·梁书;新五代史·梁本纪;资治通鉴·卷266-272"),
    ("k_houdong", "后唐", "Later Tang", "#27ae60", (923,4), (936,11), "p_licunxu", "pl_luoyang", None, "k_houjin",
     "沙陀李存勖灭后梁所建,都洛阳。庄宗、明宗两朝强盛,末为石敬瑭借契丹兵所灭。三代四帝。",
     "旧五代史·唐书;新五代史·唐本纪;资治通鉴·卷272-280"),
    ("k_houjin", "后晋", "Later Jin", "#8e44ad", (936,11), (947,1), "p_shijingtan", "pl_kaifeng", None, "k_houliaoliao",
     "石敬瑭借契丹兵灭后唐所建。割燕云十六州予契丹,自称儿皇帝。947 年为契丹所灭。",
     "旧五代史·晋书;新五代史·晋本纪;资治通鉴·卷280-286"),
    ("k_houhan", "后汉", "Later Han", "#f39c12", (947,2), (951,1), "p_liuzhiyuan", "pl_kaifeng", None, "k_houzhou",
     "刘知远在契丹北撤后建国,都开封。仅四年即亡,五代最短命。",
     "旧五代史·汉书;新五代史·汉本纪;资治通鉴·卷286-290"),
    ("k_houzhou", "后周", "Later Zhou", "#16a085", (951,2), (960,2), "p_guowei", "pl_kaifeng", None, "k_song",
     "郭威建国。世宗柴荣南征北讨、改革内政,奠北宋统一基础。960 年赵匡胤陈桥兵变代之。",
     "旧五代史·周书;新五代史·周本纪;资治通鉴·卷290-294"),
    # 十国
    ("k_qianshu", "前蜀", "Former Shu", "#e74c3c", (907,9), (925,11), "p_wangjian", "pl_chengdu", "k_tang", "k_houdong",
     "王建在四川所建。925 年为后唐所灭。",
     "新五代史·前蜀世家;十国春秋·前蜀"),
    ("k_houshu", "后蜀", "Later Shu", "#d35400", (934,1), (965,2), "p_mengzhixiang", "pl_chengdu", None, "k_song",
     "孟知祥在四川所建。965 年为北宋所灭。",
     "新五代史·后蜀世家;十国春秋·后蜀"),
    ("k_yangwu", "杨吴", "Yang Wu", "#1abc9c", (902,4), (937,10), "p_yanghangmi", "pl_jinling", "k_tang", "k_nantang",
     "杨行密奠基,唐封吴王。为南唐取代。",
     "新五代史·吴世家;十国春秋·吴"),
    ("k_nantang", "南唐", "Southern Tang", "#3498db", (937,10), (975,11), "p_libian", "pl_jinling", "k_yangwu", "k_song",
     "李昪(徐知诰)代吴所建。文化经济繁盛,灭闽、楚。975 年为北宋所灭。李煜词帝在位时亡国。",
     "新五代史·南唐世家;十国春秋·南唐;南唐书"),
    ("k_wuyue", "吴越", "Wuyue", "#2ecc71", (907,5), (978,5), "p_qianliu", "pl_hangzhou", None, "k_song",
     "钱镠所建,都杭州。东南富庶。978 年和平归宋。",
     "新五代史·吴越世家;十国春秋·吴越;吴越备史"),
    ("k_min", "闽", "Min", "#c0392b", (909,4), (945,11), "p_wangshenzhi", "pl_fuzhou", None, "k_nantang",
     "王审知所建,都福州。945 年为南唐所灭。",
     "新五代史·闽世家;十国春秋·闽"),
    ("k_chu", "楚", "Chu", "#e67e22", (907,4), (951,11), "p_mayin", "pl_changsha", None, "k_nantang",
     "马殷所建,都长沙。951 年为南唐所灭。",
     "新五代史·楚世家;十国春秋·楚"),
    ("k_nanhan", "南汉", "Southern Han", "#9b59b6", (917,8), (971,3), "p_liuyan", "pl_guangzhou", None, "k_song",
     "刘龑(刘岩)所建,都广州。971 年为北宋所灭。暴虐著称。",
     "新五代史·南汉世家;十国春秋·南汉"),
    ("k_jingnan", "荆南", "Jingnan", "#34495e", (924,3), (963,3), "p_gaojixing", "pl_jiangling", None, "k_song",
     "高季兴所建,都江陵。地小民寡,在列强间求存。963 年为北宋所灭。又称南平。",
     "新五代史·南平世家;十国春秋·荆南"),
    ("k_beihan", "北汉", "Northern Han", "#16a085", (951,2), (979,6), "p_liuchong", "pl_taiyuan", None, "k_song",
     "后周代汉后,刘崇在太原所建。依附契丹抗周/宋。979 年为北宋所灭。十国最后亡者。",
     "新五代史·东汉世家;十国春秋·北汉;资治通鉴·卷290-293"),
    # auxiliary: Tang (precursor) + Song (successor) + Khitan Liao
    ("k_tang", "唐", "Tang", "#bd3c3c", (618,1), (907,4), None, "pl_chang_an", None, "k_houliang",
     "唐朝。907 年朱温篡唐,唐亡。五代十国时期的政治前夜。",
     "新唐书;旧唐书;资治通鉴·卷265"),
    ("k_song", "宋", "Song", "#f1c40f", (960,2), (1279,2), "p_zhaokuangyin", "pl_kaifeng", None, None,
     "北宋。960 年赵匡胤陈桥兵变代后周。979 年灭北汉,统一中国本部。",
     "宋史;续资治通鉴长编"),
    ("k_liao", "契丹/辽", "Khitan/Liao", "#7f8c8d", (916,1), (1125,8), "p_yeluabaoji", "pl_liaoshangjing", None, None,
     "契丹族耶律阿保机所建,947 年改国号辽。五代时期深度介入中原事务,灭后晋。占有燕云十六州。",
     "辽史;契丹国志"),
]
# special: 唐末、宋初、辽视为"边境外围政权",不计入五代十国核心
# GeoJSON file references will be filled by gen_geojson.py
GEOJSON_MAP = {
    "k_houliang": ("houliang_peak", (907, 923)),
    "k_houdong": ("houdong_peak", (923, 936)),
    "k_houjin": ("houjin_peak", (936, 947)),
    "k_houhan": ("houhan_peak", (947, 950)),
    "k_houzhou": ("houzhou_peak", (951, 960)),
    "k_qianshu": ("qianshu_peak", (907, 925)),
    "k_houshu": ("houshu_peak", (934, 965)),
    "k_yangwu": ("yangwu_peak", (902, 937)),
    "k_nantang": ("nantang_peak", (937, 975)),
    "k_wuyue": ("wuyue_peak", (907, 978)),
    "k_min": ("min_peak", (909, 945)),
    "k_chu": ("chu_peak", (907, 951)),
    "k_nanhan": ("nanhan_peak", (917, 971)),
    "k_jingnan": ("jingnan_peak", (924, 963)),
    "k_beihan": ("beihan_peak", (951, 979)),
    "k_liao": ("liao_peak", (916, 1125)),
}

def gen_polities():
    for tup in POLITIES:
        pid, name, en, color, founded, ended, founder, capital, supplanted, ended_by, desc, src = tup
        obj = {
            "id": pid, "type": "Polity", "name": name,
            "name_en": en, "color": color,
            "founded": {"year": founded[0], "month": founded[1]},
            "ended": {"year": ended[0], "month": ended[1]},
            "capital": capital,
            "description": desc,
            "sources": src.split(";"),
        }
        if founder:
            obj["founder"] = founder
        if supplanted:
            obj["supplanted"] = supplanted
        if ended_by:
            obj["ended_by"] = ended_by
        # territory
        if pid in GEOJSON_MAP:
            gjname, (vf, vt) = GEOJSON_MAP[pid]
            obj["territory"] = [{
                "valid_from": {"year": vf},
                "valid_to": {"year": vt},
                "geojson_file": f"{gjname}.geojson",
            }]
        write(DATA / "entities" / "polities" / f"{pid[2:]}.yaml", obj)


if __name__ == "__main__":
    print(f"→ writing to {DATA}")
    gen_places()
    print(f"  ✓ {len(PLACES)} places")
    gen_polities()
    print(f"  ✓ {len(POLITIES)} polities")
    print("Done. Now run persons/battles/factions/events generators.")
