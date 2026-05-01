"""Ticket code generator."""
import random
from datetime import datetime


def generate_ticket_code() -> str:
    year = datetime.now().strftime("%Y")
    number = random.randint(1, 99999)
    return f"TKT-{year}-{number:05d}"


def generate_apply_code() -> str:
    from app.shared.constants.scoring import APPLY_CODE_PREFIX, APPLY_CODE_LENGTH
    number = random.randint(1, 10 ** APPLY_CODE_LENGTH - 1)
    return f"{APPLY_CODE_PREFIX}-{number:0{APPLY_CODE_LENGTH}d}"
