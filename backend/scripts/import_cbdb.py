"""
CBDB → YAML transformer
=======================

Strategy: seed expansion from existing 419 Person entities.
  1. For each seed person, find the matching CBDB record (by name + birth/death year).
  2. Import the seed's CBDB record (enriching birth/death/bio).
  3. Import first-hop kin and selected social associations as new Person entities.
  4. Emit relation YAMLs with since/until years.

Sources:
  - external_data/cbdb_20260704.sqlite3 (Harvard CBDB, 2026-07-04 release)

Output:
  - data/entities/persons/p_cbdb_<id>.yaml       (new persons from CBDB)
  - data/entities/places/pl_cbdb_<addr_id>.yaml   (places from CBDB ADDR_CODES)
  - data/relations/cbdb.yaml                      (all CBDB-sourced relations)
  - data/cbdb_seed_map.yaml                       (seed name → CBDB person_id, for reference)
"""

from __future__ import annotations
import sqlite3
import sys
from pathlib import Path
import yaml
import opencc

ROOT = Path(__file__).resolve().parents[2]
SQLITE_PATH = ROOT / "external_data" / "cbdb_20260704.sqlite3"
PERSONS_DIR = ROOT / "data" / "entities" / "persons"
PLACES_DIR = ROOT / "data" / "entities" / "places"
RELATIONS_FILE = ROOT / "data" / "relations" / "cbdb.yaml"
SEED_MAP_FILE = ROOT / "data" / "cbdb_seed_map.yaml"

# ---------- CBDB kin/assoc code → our relation type ----------
# Kinship: see KINSHIP_CODES. We translate the most common ones.
KIN_CODE_MAP = {
    # parents / ancestors
    62: ("father_of", "祖父"),       # FF
    75: ("father_of", "父"),         # F
    48: ("father_of", "曾祖"),        # FFF
    39: ("father_of", "高祖"),
    111: ("mother_of", "母"),         # M
    375: ("mother_of", "繼母"),
    79: ("sibling_of", "從父/伯叔父"),  # FB - treat as family
    # spouses
    134: ("spouse_of", "夫"),
    135: ("spouse_of", "妻"),
    138: ("spouse_of", "妻"),        # W1
    163: ("spouse_of", "妻"),        # W2
    164: ("spouse_of", "妻"),        # W3
    87: ("father_of", "岳父"),        # W1F — emit as father_of on the *wife*; but we don't have wife's record reliably; skip in practice
    76: ("father_of", "岳父"),
    # siblings
    125: ("sibling_of", "兄"),
    126: ("sibling_of", "弟"),
    118: ("sibling_of", "兄弟"),
    124: ("sibling_of", "姐"),
    127: ("sibling_of", "妹"),
    # children / descendants
    180: ("child_of_inv", "子"),       # P -> S, so we emit father_of if male else mother_of
    181: ("child_of_inv", "女婿"),
    176: ("child_of_inv", "女兒"),
    182: ("child_of_inv", "長子"),
    183: ("child_of_inv", "次子"),
    184: ("child_of_inv", "三子"),
    185: ("child_of_inv", "四子"),
    214: ("child_of_inv", "繼子"),
    177: ("child_of_inv", "姪子"),
    243: ("child_of_inv", "孫"),
    255: ("child_of_inv", "曾孫"),
}

# Social association codes (subset with high information value).
# We treat literary exchanges (赠诗/书序/墓志铭) as weak ties — historically these
# are exactly how literati networks formed.
ASSOC_CODE_MAP = {
    # mentor / student
    22: ("mentored_by", "為Y之學生"),       # S is student of Y
    23: ("mentor_of",   "學生為Y"),         # S has student Y
    # friend
    9:  ("friend_of", "友"),
    # politics: recommendation / coalition
    13: ("recommended_by", "推薦"),         # Y recommended S — invert below
    14: ("recommended",    "被Y推薦"),
    17: ("appreciated_by", "被Y欣賞/器重"),
    18: ("appreciated",    "欣賞/器重"),
    # written for: epigraph / biography
    44: ("epigraph_for", "為Y作墓誌銘"),
    43: ("epigraph_by",  "墓誌銘由Y所作"),
    132: ("biography_by", "傳記作者為Y"),
    133: ("biography_for","為Y作傳"),
    # --- Literary exchanges (the sinological glue of literati networks) ---
    # All map to "associated_with" — directionality is encoded in the note.
    429: ("correspondence_to", "致書Y"),
    430: ("correspondence_from","被致書由Y"),
    431: ("reply_to",      "答Y書"),
    432: ("reply_from",    "收到Y的答書"),
    437: ("poem_to",       "贈詩、文"),
    438: ("poem_from",     "收到Y的贈詩、文"),
    114: ("verse_match",   "相唱和"),
    32:  ("preface_for",   "為Y所著書作序"),
    33:  ("preface_by",    "書序由Y所作"),
    45:  ("postscript_by", "書跋由Y所作"),
    46:  ("postscript_for","為Y所著書作跋"),
    145: ("eulogy_for",    "為Y作祭文"),
    146: ("eulogy_by",     "祭文由Y所作"),
    162: ("farewell_to",   "為Y作臨別贈言"),
    163: ("farewell_from", "臨別得到Y所作贈言"),
    409: ("tombstone_by",  "墓表由Y所作"),
    410: ("tombstone_for", "為Y作墓表"),
    443: ("building_for",  "為Y之建築物題詠"),
    444: ("building_from", "建築物得到Y的題詠"),
}

# CBDB dynasty id → our polity id (for person.dynasty tagging)
# We map major dynasties only.
DY_TO_POLITY = {
    61: "k_qin", 2: "k_xihan", 29: "k_xihan", 46: "k_xin", 25: "k_donghan", 83: "k_han",
    26: "k_caowei", 53: "k_shuhan", 42: "k_dongwu",
    23: "k_xijin", 27: "k_dongjin", 82: "k_jin",
    28: "k_liu_song", 32: "k_nan_qi", 44: "k_nan_liang", 24: "k_chen",
    30: "k_beiwei", 41: "k_dong_wei", 40: "k_xi_wei",
    35: "k_bei_qi", 31: "k_bei_zhou",
    5:  "k_sui", 6: "k_tang", 77: "k_zhou_wu",
    # Five Dynasties
    34: "k_houliang", 47: "k_houtang", 48: "k_houjin", 52: "k_houhan", 49: "k_houzhou",
    7:  "k_wudai",
    11: "k_wuyue", 38: "k_ma_chu", 12: "k_min", 13: "k_nanhan",
    8:  "k_houshu", 10: "k_nantang", 55: "k_jingnan", 66: "k_beihan",
    9:  "k_yangwu", 36: "k_yangwu", 75: "k_qianshu",
    16: "k_liao", 15: "k_beisong", 78: "k_xixia", 17: "k_jin", 59: "k_xiliao",
    18: "k_yuan", 19: "k_ming", 20: "k_qing",
}


def load_seed_persons() -> list[dict]:
    """Load all existing seed Person YAMLs."""
    seeds = []
    for path in sorted(PERSONS_DIR.glob("*.yaml")):
        if path.name.startswith("p_cbdb_"):
            continue  # skip previously-imported CBDB entities
        with open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f)
        if d and d.get("type") == "Person":
            d["_source_file"] = str(path)
            seeds.append(d)
    return seeds


def main():
    if not SQLITE_PATH.exists():
        sys.exit(f"❌ CBDB SQLite not found at {SQLITE_PATH}")

    cc = opencc.OpenCC("s2t")
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print(f"✓ Opened CBDB SQLite ({SQLITE_PATH.stat().st_size // (1024*1024)} MB)")

    # 1. Match seeds → CBDB ids
    seeds = load_seed_persons()
    print(f"✓ Loaded {len(seeds)} seed persons")

    seed_map: dict[str, int] = {}   # seed_filename_noext → cbdb_personid
    enriched_seed: dict[int, dict] = {}   # cbdb_personid → enriched dict
    place_cache: dict[int, str] = {}   # addr_id → our place_id
    new_persons: dict[int, dict] = {}  # cbdb_personid → person yaml dict (new)
    new_relations: list[dict] = []

    def find_cbdb_match(name: str, born: int | None, died: int | None) -> int | None:
        """Find best CBDB match by name (s2t) + year disambiguation."""
        tname = cc.convert(name)
        # Query both simplified and traditional
        candidates = []
        for q in ({'n': name}, {'n': tname}):
            rows = cur.execute(
                "SELECT c_personid, c_name_chn, c_birthyear, c_deathyear FROM BIOG_MAIN WHERE c_name_chn=?",
                (q['n'],)).fetchall()
            for r in rows:
                candidates.append(dict(r))
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]["c_personid"]
        # Disambiguate by year proximity
        def score(c):
            s = 0
            if born and c["c_birthyear"]:
                s -= abs(c["c_birthyear"] - born) if abs(c["c_birthyear"] - born) < 30 else 100
            elif born and not c["c_birthyear"]:
                s -= 50  # prefer records with year
            if died and c["c_deathyear"]:
                s -= abs(c["c_deathyear"] - died) if abs(c["c_deathyear"] - died) < 30 else 100
            elif died and not c["c_deathyear"]:
                s -= 50
            return s
        candidates.sort(key=score)
        return candidates[0]["c_personid"]

    def cbdb_id_to_our_id(pid: int) -> str:
        return f"p_cbdb_{pid}"

    def ensure_place(addr_id: int) -> str | None:
        """Get or create our Place for a CBDB addr_id."""
        if addr_id is None or addr_id == 0:
            return None
        if addr_id in place_cache:
            return place_cache[addr_id]
        row = cur.execute(
            "SELECT c_addr_id, c_name_chn, c_name, x_coord, y_coord, c_firstyear, c_lastyear, c_admin_type FROM ADDR_CODES WHERE c_addr_id=?",
            (addr_id,)).fetchone()
        if not row:
            return None
        our_id = f"pl_cbdb_{addr_id}"
        d = dict(row)
        # Skip if no coords and no name
        if not d["c_name_chn"]:
            return None
        yaml_data = {
            "id": our_id,
            "type": "Place",
            "name": d["c_name_chn"],
            "modern_name": d["c_name_chn"],
            "category": "city",
            "sources": ["CBDB ADDR_CODES"],
        }
        if d["x_coord"] and d["y_coord"]:
            yaml_data["latitude"] = d["y_coord"]
            yaml_data["longitude"] = d["x_coord"]
        if d["c_firstyear"]:
            yaml_data["first_year"] = d["c_firstyear"]
        if d["c_lastyear"]:
            yaml_data["last_year"] = d["c_lastyear"]
        if d["c_admin_type"]:
            yaml_data["description"] = f"CBDB 行政类型:{d['c_admin_type']}"
        # Write file
        path = PLACES_DIR / f"{our_id}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(yaml_data, f, allow_unicode=True, sort_keys=False)
        place_cache[addr_id] = our_id
        return our_id

    def ensure_person(pid: int, depth: int = 0) -> str | None:
        """Get or create our Person entity for a CBDB personid."""
        if pid is None or pid == 0:
            return None
        if pid in enriched_seed:
            return enriched_seed[pid]["_our_id"]
        if pid in new_persons:
            return new_persons[pid]["id"]
        row = cur.execute(
            "SELECT c_personid, c_name_chn, c_name, c_birthyear, c_deathyear, c_female, c_dy, c_index_year, c_index_addr_id, c_surname_chn, c_mingzi_chn, c_notes "
            "FROM BIOG_MAIN WHERE c_personid=?",
            (pid,)).fetchone()
        if not row:
            return None
        d = dict(row)
        if not d["c_name_chn"] or d["c_name_chn"] == "未詳":
            return None
        our_id = cbdb_id_to_our_id(pid)
        yaml_data = {
            "id": our_id,
            "type": "Person",
            "name": d["c_name_chn"],
        }
        if d["c_birthyear"] and d["c_birthyear"] > -1000:
            yaml_data["born"] = {"year": d["c_birthyear"]}
        if d["c_deathyear"] and d["c_deathyear"] > -1000:
            yaml_data["died"] = {"year": d["c_deathyear"]}
        yaml_data["gender"] = "female" if d["c_female"] else "male"
        if d["c_index_addr_id"]:
            bp = ensure_place(d["c_index_addr_id"])
            if bp:
                yaml_data["birthplace"] = bp
        if d["c_dy"] and d["c_dy"] in DY_TO_POLITY:
            yaml_data["dynasty_ref"] = DY_TO_POLITY[d["c_dy"]]
        yaml_data["bio"] = f"CBDB ID {pid}"
        if d["c_name"]:
            yaml_data["name_en"] = d["c_name"]
        yaml_data["sources"] = ["CBDB (China Biographical Database)"]
        new_persons[pid] = yaml_data
        return our_id

    # Match all seeds first
    matched = 0
    for seed in seeds:
        name = seed.get("name")
        if not name:
            continue
        born = (seed.get("born") or {}).get("year")
        died = (seed.get("died") or {}).get("year")
        pid = find_cbdb_match(name, born, died)
        if pid:
            seed_map[Path(seed["_source_file"]).stem] = pid
            enriched_seed[pid] = {
                "_our_id": seed["id"],
                "_seed": seed,
                "_pid": pid,
            }
            matched += 1
    print(f"✓ Matched {matched} / {len(seeds)} seeds to CBDB records")

    # 2. For each matched seed, harvest kin + selected associations (1-hop)
    skipped_kin = 0
    skipped_assoc = 0
    used_pids = set(enriched_seed.keys())

    for pid, info in enriched_seed.items():
        our_id = info["_our_id"]
        # Kin relations
        kin_rows = cur.execute(
            "SELECT k.c_kin_code AS kin_code, k.c_kin_id AS kin_id, kc.c_kinrel_chn AS kinrel_chn "
            "FROM KIN_DATA k LEFT JOIN KINSHIP_CODES kc ON k.c_kin_code=kc.c_kincode "
            "WHERE k.c_personid=?",
            (pid,)).fetchall()
        for kr in kin_rows:
            k = kr["kin_code"]
            if k not in KIN_CODE_MAP:
                skipped_kin += 1
                continue
            other_pid = kr["kin_id"]
            if not other_pid:
                continue
            our_other = ensure_person(other_pid)
            if not our_other:
                continue
            mapped_rel, label = KIN_CODE_MAP[k]
            # KIN_DATA: person → kin  (e.g. kin_code=75 父 means kin IS the father)
            # c_kin_code=75 (父) means c_kin_id is the FATHER of c_personid.
            if mapped_rel == "father_of" and label in ("父", "祖父", "曾祖", "高祖", "岳父", "繼父"):
                rel = {"from": our_other, "to": our_id, "type": "father_of"}
            elif mapped_rel == "mother_of":
                rel = {"from": our_other, "to": our_id, "type": "mother_of"}
            elif mapped_rel == "spouse_of":
                rel = {"from": our_id, "to": our_other, "type": "spouse_of"}
            elif mapped_rel == "sibling_of":
                rel = {"from": our_id, "to": our_other, "type": "sibling_of"}
            elif mapped_rel == "child_of_inv":
                other_row = cur.execute("SELECT c_female FROM BIOG_MAIN WHERE c_personid=?", (other_pid,)).fetchone()
                if other_row and other_row["c_female"]:
                    rel = {"from": our_id, "to": our_other, "type": "mother_of"}
                else:
                    rel = {"from": our_id, "to": our_other, "type": "father_of"}
            else:
                continue
            rel["source"] = "CBDB KIN"
            rel["note"] = f"CBDB kinrel: {kr['kinrel_chn'] or ''}"
            new_relations.append(rel)

        # Social associations (only "important" types)
        assoc_rows = cur.execute(
            "SELECT c_assoc_code, c_assoc_id, c_assoc_first_year, c_assoc_last_year FROM ASSOC_DATA WHERE c_personid=?",
            (pid,)).fetchall()
        for ar in assoc_rows:
            ac = ar["c_assoc_code"]
            if ac not in ASSOC_CODE_MAP:
                skipped_assoc += 1
                continue
            other_pid = ar["c_assoc_id"]
            if not other_pid:
                continue
            our_other = ensure_person(other_pid)
            if not our_other:
                continue
            mapped_rel, label = ASSOC_CODE_MAP[ac]
            # In ASSOC_DATA: c_personid is the subject S, c_assoc_id is the object Y.
            # CBDB convention: c_assoc_desc "X 為Y之學生" means S IS student of Y.
            # So for code 22 (為Y之學生): subject → mentored_by → Y
            if mapped_rel == "mentored_by":
                rel = {"from": our_id, "to": our_other, "type": "mentored_by"}
            elif mapped_rel == "mentor_of":
                # S has student Y  →  Y mentored_by S
                rel = {"from": our_other, "to": our_id, "type": "mentored_by"}
            elif mapped_rel == "friend_of":
                rel = {"from": our_id, "to": our_other, "type": "allied_with"}
            elif mapped_rel == "recommended_by":
                rel = {"from": our_other, "to": our_id, "type": "served_under", "note": "推薦"}
            elif mapped_rel == "recommended":
                rel = {"from": our_id, "to": our_other, "type": "served_under", "note": "推薦"}
            elif mapped_rel == "appreciated_by":
                rel = {"from": our_other, "to": our_id, "type": "associated_with", "note": "欣賞/器重"}
            elif mapped_rel == "appreciated":
                rel = {"from": our_id, "to": our_other, "type": "associated_with", "note": "欣賞/器重"}
            elif mapped_rel.endswith("_for") or mapped_rel.endswith("_to"):
                # subject S does something FOR Y → S → associated_with → Y
                rel = {"from": our_id, "to": our_other, "type": "associated_with", "note": label}
            elif mapped_rel.endswith("_by") or mapped_rel.endswith("_from"):
                # subject S receives FROM Y → Y → associated_with → S
                rel = {"from": our_other, "to": our_id, "type": "associated_with", "note": label}
            elif mapped_rel == "verse_match":
                rel = {"from": our_id, "to": our_other, "type": "associated_with", "note": "相唱和"}
            else:
                continue
            if ar["c_assoc_first_year"] and ar["c_assoc_first_year"] > -1000:
                rel["since"] = {"year": ar["c_assoc_first_year"]}
            if ar["c_assoc_last_year"] and ar["c_assoc_last_year"] > -1000:
                rel["until"] = {"year": ar["c_assoc_last_year"]}
            rel["source"] = "CBDB ASSOC"
            new_relations.append(rel)

    print(f"✓ Kin/Assoc scanning done. Skipped unmapped kin: {skipped_kin}, assoc: {skipped_assoc}")
    print(f"✓ New persons to import: {len(new_persons)}")
    print(f"✓ New relations: {len(new_relations)}")
    print(f"✓ New places: {len(place_cache)}")

    # 3. Write new persons
    for pid, pyaml in new_persons.items():
        path = PERSONS_DIR / f"{pyaml['id']}.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(pyaml, f, allow_unicode=True, sort_keys=False)
    print(f"✓ Wrote {len(new_persons)} new person files to {PERSONS_DIR}")

    # 4. Write relations file
    with open(RELATIONS_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(new_relations, f, allow_unicode=True, sort_keys=False)
    print(f"✓ Wrote {len(new_relations)} relations to {RELATIONS_FILE}")

    # 5. Write seed map for reference
    with open(SEED_MAP_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(seed_map, f, allow_unicode=True, sort_keys=True)
    print(f"✓ Wrote seed map to {SEED_MAP_FILE}")

    conn.close()
    print("\n✅ Done.")


if __name__ == "__main__":
    main()
