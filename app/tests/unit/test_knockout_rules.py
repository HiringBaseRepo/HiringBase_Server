"""Unit tests untuk knockout rule evaluation."""
import pytest
from unittest.mock import MagicMock
from app.features.screening.services.helpers import (
    evaluate_knockout_rule as _evaluate_knockout_rule,
    find_answer_value as _find_answer_value,
    compare_numeric as _compare_numeric,
)


def _make_rule(rule_type, operator, target_value, field_key=None, rule_name="Test Rule"):
    rule = MagicMock()
    rule.rule_type = rule_type
    rule.operator = operator
    rule.target_value = target_value
    rule.field_key = field_key
    rule.rule_name = rule_name
    return rule


def _make_doc(doc_type_value):
    doc = MagicMock()
    doc.document_type.value = doc_type_value
    return doc


def _make_answer(field_key, value_text=None, value_number=None, form_field_key=None):
    answer = MagicMock()
    answer.value_text = value_text
    answer.value_number = value_number
    if form_field_key:
        answer.form_field = MagicMock()
        answer.form_field.field_key = form_field_key
    else:
        answer.form_field = None
        answer.field_key = field_key
    return answer


# =====================================================
# Document Type Tests
# =====================================================

def test_knockout_document_present():
    rule = _make_rule("document", "eq", "cv")
    docs = [_make_doc("cv")]
    assert _evaluate_knockout_rule(rule, MagicMock(), docs) is True


def test_knockout_document_missing():
    rule = _make_rule("document", "eq", "ktp")
    docs = [_make_doc("cv")]
    assert _evaluate_knockout_rule(rule, MagicMock(), docs) is False


def test_knockout_document_multiple_docs():
    rule = _make_rule("document", "eq", "ijazah")
    docs = [_make_doc("cv"), _make_doc("ktp"), _make_doc("ijazah")]
    assert _evaluate_knockout_rule(rule, MagicMock(), docs) is True


# =====================================================
# Experience Type Tests
# =====================================================

def test_knockout_experience_meets_requirement():
    rule = _make_rule("experience", "gte", "2", field_key="work_experience_years")
    answer = _make_answer("work_experience_years", value_text="3", form_field_key="work_experience_years")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[answer]) is True


def test_knockout_experience_below_requirement():
    rule = _make_rule("experience", "gte", "3", field_key="work_experience_years")
    answer = _make_answer("work_experience_years", value_text="1", form_field_key="work_experience_years")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[answer]) is False


def test_knockout_experience_no_answer_passes():
    """Jika tidak ada data pengalaman, default lulus (benefit of doubt)."""
    rule = _make_rule("experience", "gte", "2", field_key="work_experience_years")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[]) is True


# =====================================================
# Boolean Type Tests
# =====================================================

def test_knockout_boolean_bersedia_match():
    rule = _make_rule("boolean", "eq", "bersedia", field_key="willing_relocate")
    answer = _make_answer("willing_relocate", value_text="bersedia", form_field_key="willing_relocate")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[answer]) is True


def test_knockout_boolean_tidak_bersedia_reject():
    rule = _make_rule("boolean", "eq", "bersedia", field_key="willing_relocate")
    answer = _make_answer("willing_relocate", value_text="tidak", form_field_key="willing_relocate")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[answer]) is False


def test_knockout_boolean_yes_true_equivalent():
    rule = _make_rule("boolean", "eq", "yes", field_key="willing_overtime")
    answer_yes = _make_answer("willing_overtime", value_text="ya", form_field_key="willing_overtime")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[answer_yes]) is True


# =====================================================
# Education Type Tests
# =====================================================

def test_knockout_education_s1_meets_s1():
    rule = _make_rule("education", "gte", "s1", field_key="education_level")
    answer = _make_answer("education_level", value_text="s1", form_field_key="education_level")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[answer]) is True


def test_knockout_education_d3_fails_s1():
    rule = _make_rule("education", "gte", "s1", field_key="education_level")
    answer = _make_answer("education_level", value_text="d3", form_field_key="education_level")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[answer]) is False


def test_knockout_education_s2_passes_s1():
    rule = _make_rule("education", "gte", "s1", field_key="education_level")
    answer = _make_answer("education_level", value_text="s2", form_field_key="education_level")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[answer]) is True


# =====================================================
# Range / Numeric Type Tests
# =====================================================

def test_knockout_range_salary_within():
    rule = _make_rule("range", "lte", "10000000", field_key="expected_salary")
    answer = _make_answer("expected_salary", value_number=8000000, form_field_key="expected_salary")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[answer]) is True


def test_knockout_range_salary_exceeds():
    rule = _make_rule("range", "lte", "10000000", field_key="expected_salary")
    answer = _make_answer("expected_salary", value_number=15000000, form_field_key="expected_salary")
    assert _evaluate_knockout_rule(rule, MagicMock(), [], answers=[answer]) is False


# =====================================================
# Unknown rule type — default pass
# =====================================================

def test_knockout_unknown_type_default_pass():
    rule = _make_rule("unknown_type_xyz", "eq", "something")
    assert _evaluate_knockout_rule(rule, MagicMock(), []) is True


# =====================================================
# _find_answer_value Tests
# =====================================================

def test_find_answer_value_found():
    answer = _make_answer("test_key", value_text="hello", form_field_key="test_key")
    result = _find_answer_value("test_key", [answer])
    assert result == "hello"


def test_find_answer_value_not_found():
    answer = _make_answer("other_key", value_text="hello", form_field_key="other_key")
    result = _find_answer_value("test_key", [answer])
    assert result is None


def test_find_answer_value_empty_answers():
    result = _find_answer_value("test_key", [])
    assert result is None


def test_find_answer_value_no_field_key():
    result = _find_answer_value(None, [MagicMock()])
    assert result is None
