# SQL translation

## What it does

The translator rewrites PostgreSQL SQL into Db2 SQL with safe rules. It runs before any agent. Rules are small, named, and recorded.

## Rules in v1

- `cast_double_colon`: `id::text` becomes `CAST(id AS VARCHAR(4000))`. Only known types are matched, so the rule never swallows the next word.
- `ilike_to_upper_like`: `name ILIKE 'a%'` becomes `UPPER(name) LIKE UPPER('a%')`.
- `limit_offset_to_fetch`: `LIMIT 10` becomes `FETCH FIRST 10 ROWS ONLY`. With offset it becomes `OFFSET 5 ROWS FETCH NEXT 10 ROWS ONLY`.
- `now_to_current_timestamp`: `now()` becomes `CURRENT_TIMESTAMP`.
- `random_to_rand`: `random()` becomes `RAND()`.
- `substring_from_to_comma`: `SUBSTRING(name FROM 2 FOR 3)` becomes `SUBSTRING(name, 2, 3)`.

## Untranslatable patterns

These are flagged and sent for human or agent review:

- JSON arrow operators (`->`, `->>`).
- Regex operators (`~`, `~*`).
- Array literals.
- `RETURNING` clauses.
- Dollar quoting.
- `SERIAL` type.

## Important

A clean translation is not proof. The translated SQL still runs on Db2 through the Parity Engine and must match the source result before anyone calls it safe.
