"""Tests for KB search reuse stats."""

from parity.kb.store import InMemoryKb, KnownDifference, SearchStats


def test_stats_count_hits_and_misses():
    kb = InMemoryKb()
    kb.add(KnownDifference(title="t", source_pattern="ILIKE", db2_pattern="UPPER", verified=True))
    kb.search("ILIKE")
    kb.search("does not match anything at all")
    stats = kb.stats()
    assert stats.searches == 2
    assert stats.hits == 1
    assert stats.misses == 1
    assert stats.hit_rate == 0.5


def test_stats_empty_store():
    stats = InMemoryKb().stats()
    assert stats.searches == 0
    assert stats.hit_rate == 0.0


def test_search_stats_defaults():
    stats = SearchStats()
    assert stats.hits == 0
    assert stats.hit_rate == 0.0
