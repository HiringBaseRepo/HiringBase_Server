from typing import Any, Dict, List
from sqlalchemy import inspect

def get_model_snapshot(model: Any, exclude_columns: List[str] = None) -> Dict[str, Any]:
    """
    Convert a SQLAlchemy model instance into a dictionary of its current attributes.
    Useful for capturing 'old_values' before an update.
    """
    if exclude_columns is None:
        exclude_columns = ['created_at', 'updated_at', 'id']
        
    ins = inspect(model)
    return {
        c.key: getattr(model, c.key)
        for c in ins.mapper.column_attrs
        if c.key not in exclude_columns
    }
