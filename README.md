# Parity

Parity proves that your SQL gives the same result on a new database.

When a team moves an app to IBM Db2, most tools only convert the code. They do not prove the result. A query can run with no error and still return a wrong answer. You find out weeks later in a report, an invoice, or a dashboard. That is a silent bug. Parity exists to catch it before users do.

Parity takes SQL from your current app, runs it on the old database and on Db2, and compares the result row by row. It only calls a query safe when both databases give the same answer on normal data and on tricky edge case data.

## Why this matters

- A syntax error is loud. Someone fixes it fast.
- A wrong result is silent. No error. No warning. Wrong business data.
- Manual comparison is slow, so teams check only a few queries.
- Knowledge about database differences sits with a few senior people.

Parity makes the check automatic, repeatable, and hard to fake.

## How it works

The rule is simple:

> The model proposes. Execution decides.

AI agents suggest a translation, test data, and a fix. A plain Python engine runs both queries and compares the result. No model is ever allowed to say two queries are the same. Only real execution on both databases can say that.

1. **Ingest.** Read SQL from files, query logs, or ORM output. Tag unsafe or random queries.
2. **Translate.** Apply safe rules first. Use an agent only for hard cases. Save every version.
3. **Generate edge case data.** NULL values, empty strings, spaces, Unicode, extreme numbers, timezone dates, mixed case. Load the exact same data into both databases.
4. **Run and compare.** Execute on PostgreSQL and Db2. Compare in plain code. Return MATCH, MISMATCH, or ERROR with the first wrong row.
5. **Diagnose.** On a mismatch, search a knowledge base in Db2 for similar known differences.
6. **Fix and re-prove.** Propose a rewrite. Run everything again. Accept the fix only if all cases match. After 3 tries, send it to a human.
7. **Learn.** Save every verified fix in Db2 with its proof. The next run starts smarter.
8. **Report.** One command gives an HTML report and a CI exit code.

## What you get

- Proof, not opinion. Every verdict comes from running both databases.
- Edge case tests by default. Not just happy path data.
- A searchable memory of database differences in Db2.
- Full replay. A recorded run can be repeated offline with no API key.
- CI ready. The build fails when parity is lost.
- Safe by design. Disposable containers only. Read only queries on the source. No production data sent to a model.

## Quick start

```bash
git clone https://github.com/Amitk003/Parity.git
cd Parity
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS or Linux: source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d
parity run --help
```

Full steps are in [docs/setup.md](docs/setup.md).

## Architecture in 30 seconds

- **Parity Engine:** plain Python. Runs queries, normalizes results, compares them. This is the only judge.
- **Agents:** Translator, Fuzzer, Diagnostician, Fixer. They propose. They never judge.
- **Controller:** a Python flow that sets strict limits. Max 3 fix tries. Token and time budgets.
- **IBM Db2:** the real target under test, the vector knowledge base, and the system of record for runs, results, and history.
- **LLM gateway:** one client for all model calls, with cache, budgets, and provider fallback ending in a local model.

See [docs/architecture.md](docs/architecture.md) for the full design.

## Status

Parity is under active development. Version 1 supports PostgreSQL as the source and IBM Db2 12.1.2 or later as the target. Parity gives strong evidence from real execution. It is not a formal mathematical proof. It cannot find a difference that its test data never triggers. We say so in the report instead of hiding it.

## License

MIT. See the repository for details.
