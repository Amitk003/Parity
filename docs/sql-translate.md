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
- `alias_expressions`: gives a name to every unaliased select item. Db2 names an unaliased expression by its text, for example `1` or `2`. Postgres names a function call by the function and any other expression by `?column?`. The rule uses a select list scanner, not a regex, so it never touches a WHERE clause, a GROUP BY, an ORDER BY, or a function call inside another function. An item that already has a name is left alone. It replaces the earlier `aggregate_alias` rule, which handled only aggregates and had a known limit with a bare `COUNT(*)` at the end of an ORDER BY.
- `offset_to_rows`: `OFFSET 2` becomes `OFFSET 2 ROWS`. Db2 needs the ROWS keyword, Postgres does not. The rule does not touch the output of the limit rule.

The alias rule reads the select list with `src/parity/translate/select_list.py`. It tracks string literals, quoted identifiers, comments, and parenthesis depth. A comma inside a function call is not a separator, and an expression in a WHERE clause is not a select item.

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
