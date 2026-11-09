# Divergence catalog

This page lists the Postgres versus Db2 differences that Parity has actually seen on live databases. Only differences seen on both databases count as real. Hypotheses stay hypotheses.

## Confirmed divergences

### 1. Unaliased aggregate column name

- Query: `SELECT COUNT(*) FROM demo_users`
- Postgres column name: `count`
- Db2 column name: `1`
- Category: COLUMN_NAME
- Why it matters: the query is a valid silent mismatch. Both databases run it, but the column name differs.
- Fix: the `aggregate_alias` rule rewrites a bare aggregate to `COUNT(*) AS COUNT`. After the fix the same query returns MATCH on live databases.

### 2. Trailing space and Unicode text

- Input: fuzzed rows with a trailing space and with Unicode text
- Source result: kept the trailing space and the accented character
- Target result: returned an empty string for those rows
- Category: VALUE
- Why it matters: text handling differs on Db2 12.1.5.0 for these edge case values, so a migration can change answers without an error.
- Status: open. This is the leading live demo target for the Diagnostician agent.

### 3. SELECT without FROM

- Query: `SELECT 1`
- Postgres: returns `1`
- Db2: fails with SQL0104N
- Category: ERROR
- Why it matters: simple sanity queries used in health checks can fail on Db2 even when they pass on Postgres.

### 4. Expression SELECTs without FROM

- Queries: `SELECT 'a ' = 'a'`, `SELECT LENGTH('café')`, `SELECT ROUND(2.5)`, `SELECT CASE WHEN '' IS NULL THEN 'null' ELSE 'notnull' END`, `SELECT 1/2`, `SELECT 0.1 + 0.2`, `SELECT 'HELLO' LIKE 'hello'`
- Postgres: all return a value
- Db2: all fail with an error
- Category: ERROR
- Why it matters: the same root cause as entry 3, but wider. Any expression-only query fails on Db2. Probes in `samples/probes.sql` reproduce all of them.

### 5. Unaliased scalar expression column name

- Query: `SELECT UPPER(name) FROM demo_users WHERE id = 1`
- Postgres column name: `upper`
- Db2 column name: `1`
- Category: COLUMN_NAME
- Why it matters: the mismatch is not limited to aggregates. Any unaliased function call in the select list gets the expression text as its name on Db2.
- Status: open. The `aggregate_alias` rule covers aggregates only. Extending it to scalar functions is future work.

## Matched probes (no divergence)

These hypotheses were tested live and both databases agreed:

- `SELECT name FROM demo_users ORDER BY name` including NULL ordering
- `SELECT COUNT(*) FROM demo_users WHERE name IS NULL`

## Hypotheses still to confirm

These are expected from the proposal but have not been reproduced on live databases by Parity yet. Do not quote them as facts.

- NULL versus empty string in comparison and joins.
- Rounding rules for decimal values that need half-up or half-even rounding.
- Timezone offset handling for timestamp with time zone values.
- Implicit cast behavior that changes values between the databases.
- Mixed case sort order beyond the tested sample data.

## How to add a new entry

1. Run the probe on both databases.
2. Record the SQL, both outputs, and the category.
3. Add the query to `samples/probes.sql`.
4. Add a row here with status confirmed or open.

## Known limits

This catalog is small. It grows as the probe suite grows. It never claims a difference that has not been seen on both databases.
