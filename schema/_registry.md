# Schema Registry

The type system is **data-driven**. Each node and relation type is declared in a YAML file here; `scripts/registry.py` reads them and generates:
- JSON Schema (frontend validation)
- TypeScript type stubs (frontend dev)
- Data dictionary (docs/data-dictionary.md)

## Adding a new node type

1. Create `schema/<type>.yaml` (copy `person.yaml` as template).
2. Drop YAML data files in `data/entities/<type>s/`.
3. Re-run `scripts/registry.py` to regenerate the data dictionary and TS stubs.

No code changes needed. Frontend and backend pick up the new type automatically.

## Adding a new relation type

Just use it in `data/relations/*.yaml`. Relations are free-form (`type` is a string field), but should be registered in `schema/relations.yaml` for documentation and UI styling.

## Field types

| Type        | Description                                      |
|-------------|--------------------------------------------------|
| `string`    | Short text                                       |
| `text`      | Long text (multiline)                            |
| `int`       | Integer                                          |
| `year`      | Integer year (negative = BCE)                    |
| `year_month`| `{year, month?}`                                 |
| `enum`      | One of `options`                                 |
| `array`     | List of `items` type                             |
| `ref`       | Reference to another entity by `id` (`to:` type) |
| `url`       | URL string                                       |
| `geojson_ref` | File reference under `data/geo/`               |

## Extensibility

Every node type carries `ext: allow` by default — entities may have an `ext` map of arbitrary key-value pairs. This is the escape hatch: experimental fields live there until promoted to formal schema fields.

## Currently registered types

| Type      | Label       | File           |
|-----------|-------------|----------------|
| Person    | 人物        | person.yaml    |
| Polity    | 政权        | polity.yaml    |
| Faction   | 派系/集团   | faction.yaml   |
| Event     | 事件        | event.yaml     |
| Battle    | 战役        | battle.yaml    |
| Place     | 地点        | place.yaml     |
| Title     | 官职/封号   | title.yaml     |
