import sqlite3
import json
import argparse
from pathlib import Path
from typing import Any, Dict, Optional


def load_db(db_path: Path) -> Dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT file, data FROM storage")
    rows = cur.fetchall()
    conn.close()

    result = {}
    for file_key, raw_json in rows:
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            parsed = raw_json
        result[file_key] = parsed

    return result

def merge_maps(specific: Optional[dict], wildcard: Optional[dict]) -> Optional[dict]:
    """Wildcard (base) + specific (override) merge: specific überschreibt wildcard-Einträge."""
    if wildcard is None:
        return specific
    if specific is None:
        return wildcard
    merged = dict(wildcard)
    merged.update(specific)
    return merged

def apply_mapping(value: Any, map_spec: Optional[Dict[str, Any]]) -> Any:
    """
    Rekursive Mapping-Funktion mit Support für:
      - explizite Schlüssel
      - wildcard '*' Regeln
      - rule als string (Template) oder dict {"name": "...", "map": {...}}
      - automatische Umbenennung bei Key-Kollisionen
    """
    if map_spec is None:
        return value

    # dict: mappe keys
    if isinstance(value, dict) and isinstance(map_spec, dict):
        new_obj: Dict[str, Any] = {}
        explicit = {k: v for k, v in map_spec.items() if k != "*"}
        wildcard_rule = map_spec.get("*")

        for old_k, old_v in value.items():
            # bestimme welche rule gilt: explizit > wildcard > none
            if old_k in explicit:
                rule = explicit[old_k]
            else:
                rule = wildcard_rule

            # default
            new_key = old_k
            nested_map = None

            if rule is None:
                # keine Regel: behalte key
                new_key = old_k
            elif isinstance(rule, str):
                # string template: formatiert mit {key}
                try:
                    new_key = rule.format(key=old_k)
                except Exception:
                    new_key = rule  # fallback falls format fehlschlägt
            elif isinstance(rule, dict):
                name_template = rule.get("name", old_k)
                try:
                    new_key = name_template.format(key=old_k)
                except Exception:
                    new_key = name_template
                nested_map = rule.get("map")
            else:
                new_key = old_k

            # rekursiv auf child anwenden, falls nested_map vorhanden
            if nested_map:
                old_v = apply_mapping(old_v, nested_map)
            else:
                old_v = old_v

            # doppelte Zielnamen verhindern, Suffix mit Original-Key anhängen
            if new_key in new_obj:
                new_key = f"{new_key}_{old_k}"

            new_obj[new_key] = old_v

        return new_obj

    # list: mapping auf jedes Element anwenden (häufig werden list-elements dicts sein)
    if isinstance(value, list):
        # Wenn map_spec ein dict mit '*' für Elemente hat, nutze dieses, sonst nutze map_spec direkt.
        elem_spec = None
        if isinstance(map_spec, dict) and "*" in map_spec:
            elem_spec = map_spec["*"]
        else:
            elem_spec = map_spec
        return [apply_mapping(elem, elem_spec) for elem in value]

    # primitive: nichts zu tun
    return value

def sort_json_keys(obj):
    if isinstance(obj, dict):
        # prüfen ob alle keys numerisch sind
        if all(str(k).isdigit() for k in obj.keys()):
            sorted_items = sorted(obj.items(), key=lambda x: int(x[0]))
        else:
            sorted_items = sorted(obj.items(), key=lambda x: x[0])

        return {k: sort_json_keys(v) for k, v in sorted_items}

    if isinstance(obj, list):
        return [sort_json_keys(v) for v in obj]

    return obj

def transform(storage: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
    """
    komplette Transformationspipeline:
      - file_map anwenden (neuer Dateiname für Anzeige)
      - JSON sortieren (deterministische Reihenfolge)
      - data_map (merge wildcard + specific) anwenden, wobei file-specific anhand des NEUEN Dateinamens gesucht wird
    """
    file_map = mapping.get("file_map", {})
    data_map = mapping.get("data_map", {})

    out: Dict[str, Any] = {}

    for old_file, raw_value in storage.items():
        new_file = file_map.get(old_file, old_file)

        # sortieren bevor mapping angewendet wird
        sorted_value = sort_json_keys(raw_value)

        # hole file-spezifisches mapping nach neuem Dateinamen
        specific = data_map.get(new_file)
        wildcard = data_map.get("*")
        effective_map = merge_maps(specific, wildcard)

        mapped = apply_mapping(sorted_value, effective_map)
        out[new_file] = mapped

    return out

def print_result(original: Dict[str, Any], mapped: Dict[str, Any]):
    #print("\n--- ORIGINAL ---\n")
    #for k, v in original.items():
    #    print("=" * 60)
    #    print(f"{k}")
    #    print(json.dumps(v, indent=2, ensure_ascii=False))

    print("\n--- MAPPED (Anzeige only) ---\n")
    for k, v in mapped.items():
        print("=" * 60)
        print(f"{k}")
        print(json.dumps(v, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("db", type=Path)
    parser.add_argument("mapping", type=Path)
    args = parser.parse_args()

    storage = load_db(args.db)

    if not args.mapping.exists():
        raise FileNotFoundError("Mapping file not found")

    with args.mapping.open("r", encoding="utf-8") as f:
        mapping = json.load(f)

    mapped = transform(storage, mapping)

    print_result(storage, mapped)


if __name__ == "__main__":
    main()