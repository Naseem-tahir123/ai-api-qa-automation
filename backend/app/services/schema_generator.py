from typing import Dict, Any, Type
from pydantic import create_model, BaseModel

def generate_dynamic_model(model_name: str, fields_schema: Dict[str, Any]) -> Type[BaseModel]:
    """
    OpenAPI fields dictionary ko dynamically Pydantic Model mein badalta hai.
    Example input: {"username": "str", "age": "int", "email": "str"}
    """
    pydantic_fields = {}
    
    # Har field ke type ko Python datatype mein map karna
    type_mapping = {
        "str": str,
        "int": int,
        "float": float,
        "bool": bool
    }
    
    for field_name, field_type_str in fields_schema.items():
        # Type check karna, default 'str' agar kuch samajh na aaye
        python_type = type_mapping.get(field_type_str, str)
        
        # Pydantic v2 syntax: (Type, DefaultValue)
        # Hum default value None rakh rahe hain taake tests asani se empty fields bhej sakein
        pydantic_fields[field_name] = (python_type, None)
        
    # Dynamically model banana
    return create_model(model_name, **pydantic_fields)