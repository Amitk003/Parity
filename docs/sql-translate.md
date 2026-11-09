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
- `aggregate_alias`: a bare `COUNT(*)` becomes `COUNT(*) AS COUNT`. Db2 names an unaliased aggregate column by its expression text, Postgres names it by the function. The alias makes both return the same name. Applied to `COUNT`, `SUM`, `MIN`, `MAX`, and `AVG` only in the select list position, which means before `,`, `)`, `FROM`, or the end of the query. `HAVING COUNT(*) > 1` and `ORDER BY COUNT(*) DESC` are left alone. One known limit: a bare `COUNT(*)` at the very end of `ORDER BY` gets aliased by mistake, the query then fails loudly on Db2. Alias those by hand today.

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
