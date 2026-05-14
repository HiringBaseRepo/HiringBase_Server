"""Knockout rule helpers — dipisah dari router agar bisa di-import untuk testing.

Berisi semua fungsi evaluasi rule yang TIDAK bergantung pada FastAPI context.
"""
from __future__ import annotations

from typing import Optional
from app.shared.enums.knockout import KnockoutOperator, KnockoutRuleType


def evaluate_knockout_rule(rule, application, docs: list, answers: list = None) -> bool:
    """Evaluasi knockout rule secara deterministik.

    Returns:
        True  → rule LULUS (kandidat boleh lanjut)
        False → rule GAGAL (knockout action berlaku)

    Rule types:
    - document  : cek ketersediaan dokumen wajib
    - experience: cek pengalaman kerja vs threshold
    - education : cek level pendidikan vs threshold
    - boolean   : cek jawaban form (yes/no)
    - range     : cek nilai numerik dalam rentang
    """
    if answers is None:
        answers = []

    rule_type = (rule.rule_type or "").lower()
    operator = normalize_knockout_operator(rule.operator or KnockoutOperator.EQ.value)
    target = rule.target_value

    # --- Document type ---
    if rule_type == KnockoutRuleType.DOCUMENT.value:
        doc_types = {d.document_type.value for d in docs}
        return target in doc_types

    # --- Experience type ---
    if rule_type == KnockoutRuleType.EXPERIENCE.value:
        answer_val = find_answer_value(rule.field_key, answers)
        if answer_val is not None:
            try:
                years = float(answer_val)
                req = float(target)
                return compare_numeric(years, req, operator)
            except (ValueError, TypeError):
                pass
        return True  # benefit of the doubt

    # --- Education type ---
    if rule_type == KnockoutRuleType.EDUCATION.value:
        from app.shared.constants.scoring import EDUCATION_RANK
        answer_val = find_answer_value(rule.field_key, answers)
        if answer_val is not None:
            cand_rank = EDUCATION_RANK.get(str(answer_val).lower().replace(".", "").replace(" ", ""), 0)
            req_rank = EDUCATION_RANK.get(target.lower().replace(".", "").replace(" ", ""), 0)
            if cand_rank == 0 or req_rank == 0:
                return True
            return compare_numeric(cand_rank, req_rank, operator)
        return True

    # --- Boolean type ---
    if rule_type == KnockoutRuleType.BOOLEAN.value:
        answer_val = find_answer_value(rule.field_key, answers)
        if answer_val is not None:
            answer_normalized = str(answer_val).lower().strip()
            target_normalized = target.lower().strip()
            truthy = {"yes", "true", "ya", "bersedia", "iya", "1"}
            answer_bool = answer_normalized in truthy
            target_bool = target_normalized in truthy
            if operator in ("eq", "=", "=="):
                return answer_bool == target_bool
            if operator in ("neq", "!=", "<>"):
                return answer_bool != target_bool
        return True

    # --- Range / numeric type ---
    if rule_type == KnockoutRuleType.RANGE.value:
        answer_val = find_answer_value(rule.field_key, answers)
        if answer_val is not None:
            try:
                val = float(answer_val)
                req = float(target)
                return compare_numeric(val, req, operator)
            except (ValueError, TypeError):
                pass
        return True

    # Default: tidak dikenal → beri lulus
    return True


def find_answer_value(field_key: Optional[str], answers: list):
    """Cari nilai dari application answers berdasarkan field_key."""
    if not field_key or not answers:
        return None
    for answer in answers:
        fk = None
        if hasattr(answer, "form_field") and answer.form_field:
            fk = answer.form_field.field_key
        elif hasattr(answer, "field_key"):
            fk = answer.field_key
        if fk == field_key:
            if hasattr(answer, "value_text") and answer.value_text is not None:
                return answer.value_text
            if hasattr(answer, "value_number") and answer.value_number is not None:
                return answer.value_number
    return None


def compare_numeric(value: float, target: float, operator: str) -> bool:
    """Bandingkan dua nilai numerik berdasarkan operator."""
    op_map = {
        "eq": value == target,
        "=": value == target,
        "==": value == target,
        "neq": value != target,
        "!=": value != target,
        "gt": value > target,
        ">": value > target,
        "gte": value >= target,
        ">=": value >= target,
        "lt": value < target,
        "<": value < target,
        "lte": value <= target,
        "<=": value <= target,
    }
    return op_map.get(operator, True)


def normalize_knockout_operator(operator: str) -> str:
    """Normalize supported operator aliases into canonical knockout operator value."""
    alias_map = {
        "=": KnockoutOperator.EQ.value,
        "==": KnockoutOperator.EQ.value,
        "<>": KnockoutOperator.NEQ.value,
        "!=": KnockoutOperator.NEQ.value,
        ">": KnockoutOperator.GT.value,
        ">=": KnockoutOperator.GTE.value,
        "<": KnockoutOperator.LT.value,
        "<=": KnockoutOperator.LTE.value,
    }
    normalized = (operator or "").strip().lower()
    if normalized in {item.value for item in KnockoutOperator}:
        return normalized
    return alias_map.get(normalized, normalized)
