from typing import Dict, Any, Type
from pydantic import create_model, BaseModel

def generate_dynamic_model(model_name: str, fields_schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    Create a Pydantic model dynamically from an OpenAPI fields dictionary.
    Example input: {"username": "str", "age": "int", "email": "str"}
    """
    pydantic_fields = {}
    
    # Map each schema field to a Python type.
    type_mapping = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool
    }
    
    for field_name, field_type_str in fields_schema.items():
        # Use `str` as the fallback for unrecognized types.
        python_type = type_mapping.get(field_type_str, str)
        
        # Pydantic v2 syntax: (Type, DefaultValue)
        # Default fields to None so tests can send empty values when needed.
        pydantic_fields[field_name] = (python_type, None)
        
    # Create the Pydantic model dynamically.
    return create_model(model_name, **pydantic_fields)
