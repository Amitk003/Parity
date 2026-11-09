# Knowledge base

## What it does

The knowledge base stores known database differences and verified fixes. Agents search it before they translate or fix. Verified fixes come back as hints. Unverified guesses never come back.

## Embeddings

`src/parity/kb/embeddings.py` holds a deterministic hashing embedder. It makes 384 dim vectors with no model download and no network. The interface matches a sentence transformer embedder, so a neural model can replace it later without changing callers.

## Store

`src/parity/kb/store.py` holds two stores:

- `InMemoryKb` for tests and local runs.
- `Db2Kb` for production. It uses the `known_difference` table with a `VECTOR(384, FLOAT32)` column and `VECTOR_DISTANCE` with COSINE.

Workflow:

1. A fix is verified by execution.
2. It is added as a candidate.
3. A human approves or rejects it.
4. Search returns verified entries only, closest first.

Verified entries cannot be rejected. Unknown titles raise a clear error.

## Honest limit

Hashing embeddings are weaker than neural embeddings for SQL meaning. Search also needs structured filters in a later branch. The verified only rule is the main defense against bad entries.
