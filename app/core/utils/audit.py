from datetime import datetime
from typing import Any, Dict, List
from sqlalchemy import inspect

def get_model_snapshot(model: Any, exclude_columns: List[str] = None) -> Dict[str, Any]:
    """
    Convert a SQLAlchemy model instance into a dictionary of its current attributes.
    Handles datetime serialization for JSON columns.
    """
    if exclude_columns is None:
        exclude_columns = ['created_at', 'updated_at', 'id']
        
    ins = inspect(model)
    res = {}
    for c in ins.mapper.column_attrs:
        if c.key in exclude_columns:
            continue
        val = getattr(model, c.key)
        if isinstance(val, datetime):
            val = val.isoformat()
        res[c.key] = val
    return res
