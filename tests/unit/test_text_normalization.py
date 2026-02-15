"""Unit tests for text normalization and fuzzy matching utilities."""

import pytest

from app.utils.text_normalization import (
    fuzzy_token_find,
    fuzzy_token_match,
    normalize_for_warning,
    normalize_loose,
    normalize_strict,
)


class TestNormalizeLoose:
    def test_lowercases(self):
        assert normalize_loose("HELLO World") == "hello world"

    def test_strips_punctuation(self):
        assert normalize_loose("Stone's Throw!") == "stones throw"

    def test_collapses_whitespace(self):
        assert normalize_loose("brand   name\n here") == "brand name here"

    def test_normalizes_unicode_quotes(self):
        assert normalize_loose("\u2018quoted\u2019") == "quoted"

    def test_empty_string(self):
        assert normalize_loose("") == ""


class TestNormalizeStrict:
    def test_preserves_case(self):
        assert normalize_strict("GOVERNMENT WARNING") == "GOVERNMENT WARNING"

    def test_collapses_whitespace_only(self):
        assert normalize_strict("hello   world\nfoo") == "hello world foo"


class TestNormalizeForWarning:
    def test_strips_everything_except_alphanumerics(self):
        assert normalize_for_warning("GOVERNMENT WARNING: (1)") == "GOVERNMENTWARNING1"

    def test_preserves_case(self):
        assert normalize_for_warning("Surgeon General") == "SurgeonGeneral"


class TestFuzzyTokenMatch:
    def test_exact_match(self):
        assert fuzzy_token_match("hello", "this is hello world") is True

    def test_one_char_difference(self):
        # "bott1ing" is 1 char off from "bottling"
        assert fuzzy_token_match("bottling", "this is bott1ing company") is True

    def test_too_many_differences(self):
        assert fuzzy_token_match("bottling", "this is xxxxxxxx company") is False

    def test_no_false_positive_on_substrings(self):
        # "india" should NOT match a substring within a longer word like "indicating"
        assert fuzzy_token_match("india", "this is indicating something") is False

    def test_matches_whole_word_fuzzy(self):
        # "indla" is 1 char off from "india"
        assert fuzzy_token_match("india", "based in indla somewhere") is True

    def test_empty_inputs(self):
        assert fuzzy_token_match("", "some text") is False
        assert fuzzy_token_match("hello", "") is False


class TestFuzzyTokenFind:
    def test_returns_matched_word(self):
        assert fuzzy_token_find("bottling", "this is bott1ing co") == "bott1ing"

    def test_exact_match_returns_token(self):
        assert fuzzy_token_find("hello", "say hello there") == "hello"

    def test_no_match_returns_none(self):
        assert fuzzy_token_find("xyz", "abc def ghi") is None
