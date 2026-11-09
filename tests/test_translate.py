"""Tests for the rule translator."""

import pytest

from parity.translate.rules import find_untranslatable, list_rules, translate


def test_clean_query_unchanged():
    result = translate("SELECT id FROM users WHERE id = 1")
    assert result.db2_sql == "SELECT id FROM users WHERE id = 1"
    assert result.applied_rules == ()
    assert result.untranslatable == ()


def test_cast_rule():
    result = translate("SELECT id::text FROM users")
    assert result.db2_sql == "SELECT CAST(id AS VARCHAR(4000)) FROM users"
    assert "cast_double_colon" in result.applied_rules


def test_cast_int_rule():
    result = translate("SELECT x::int FROM t")
    assert "CAST(x AS INTEGER)" in result.db2_sql


def test_ilike_rule():
    result = translate("SELECT name FROM users WHERE name ILIKE 'a%'")
    assert "UPPER(name) LIKE UPPER('a%')" in result.db2_sql


def test_limit_rule():
    result = translate("SELECT id FROM users LIMIT 10")
    assert "FETCH FIRST 10 ROWS ONLY" in result.db2_sql


def test_limit_offset_rule():
    result = translate("SELECT id FROM users LIMIT 10 OFFSET 5")
    assert "OFFSET 5 ROWS FETCH NEXT 10 ROWS ONLY" in result.db2_sql


def test_now_and_random_rules():
    assert "CURRENT_TIMESTAMP" in translate("SELECT now()").db2_sql
    assert "RAND()" in translate("SELECT random()").db2_sql


def test_substring_rule():
    result = translate("SELECT SUBSTRING(name FROM 2 FOR 3) FROM users")
    assert "SUBSTRING(name, 2, 3)" in result.db2_sql


def test_untranslatable_json_arrow():
    result = translate("SELECT data->>'key' FROM t")
    assert "json_arrow_operator" in result.untranslatable
    assert result.needs_agent is True


def test_untranslatable_returning():
    assert "returning_clause" in find_untranslatable("DELETE FROM t RETURNING id")


def test_empty_sql_rejected():
    with pytest.raises(ValueError):
        translate("   ")


def test_rules_listed():
    rules = list_rules()
    assert "cast_double_colon" in rules
    assert "ilike_to_upper_like" in rules
    assert len(rules) >= 6


def test_combined_rewrites_recorded():
    result = translate("SELECT id::int FROM users WHERE name ILIKE 'a%' LIMIT 5")
    assert set(result.applied_rules) == {"cast_double_colon", "ilike_to_upper_like", "limit_offset_to_fetch"}
