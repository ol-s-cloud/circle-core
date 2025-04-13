"""Configuration schema implementation for Circle Core.

This module provides schema definition and validation for configuration.
"""

import re
import json
from typing import Dict, List, Optional, Any, Set, Union, Type, TypeVar, Generic, Callable
from dataclasses import dataclass, field, is_dataclass, asdict

from .interface import ConfigSchema, ValidationResult, ValidationError, ValidationLevel


T = TypeVar('T')


@dataclass
class SchemaField:
    """Schema field definition."""
    
    name: str
    type: Type
    required: bool = True
    default: Any = None
    description: str = ""
    validators: List[Callable[[Any], Optional[str]]] = field(default_factory=list)
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate a value against this field.
        
        Args:
            value: Value to validate
            
        Returns:
            Error message if invalid, None if valid
        """
        # Check if required
        if value is None:
            if self.required:
                return "Required field is missing"
            return None
        
        # Check type
        if not isinstance(value, self.type) and self.type is not Any:
            return f"Expected type {self.type.__name__}, got {type(value).__name__}"
        
        # Run validators
        for validator in self.validators:
            error = validator(value)
            if error:
                return error
        
        return None


class JsonSchema(ConfigSchema[Dict[str, Any]]):
    """JSON schema implementation."""
    
    def __init__(self, schema: Dict[str, Any]):
        """Initialize JSON schema.
        
        Args:
            schema: JSON schema dictionary
        """
        self.schema = schema
    
    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration against the schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Validation result
        """
        errors = []
        self._validate_object(config, self.schema, "", errors)
        return ValidationResult(not errors, errors)
    
    def _validate_object(self, obj: Dict[str, Any], schema: Dict[str, Any], path: str, errors: List[ValidationError]) -> None:
        """Validate an object against a schema.
        
        Args:
            obj: Object to validate
            schema: Schema to validate against
            path: Path to the object
            errors: List to append errors to
        """
        # Check required properties
        required = schema.get("required", [])
        for prop in required:
            if prop not in obj:
                errors.append(ValidationError(
                    f"{path}.{prop}" if path else prop,
                    f"Required property '{prop}' is missing"
                ))
        
        # Check properties
        properties = schema.get("properties", {})
        for name, prop_schema in properties.items():
            prop_path = f"{path}.{name}" if path else name
            
            if name in obj:
                value = obj[name]
                self._validate_value(value, prop_schema, prop_path, errors)
            elif "default" in prop_schema:
                # Property is optional and has a default value
                pass
            elif name in required:
                # Already reported above
                pass
            else:
                # Optional property with no default
                pass
        
        # Check additional properties
        additional_properties = schema.get("additionalProperties", True)
        if additional_properties is False:
            for name in obj:
                if name not in properties:
                    errors.append(ValidationError(
                        f"{path}.{name}" if path else name,
                        f"Additional property '{name}' is not allowed"
                    ))
        elif additional_properties is not True:
            # additionalProperties is a schema
            for name in obj:
                if name not in properties:
                    prop_path = f"{path}.{name}" if path else name
                    self._validate_value(obj[name], additional_properties, prop_path, errors)
    
    def _validate_value(self, value: Any, schema: Dict[str, Any], path: str, errors: List[ValidationError]) -> None:
        """Validate a value against a schema.
        
        Args:
            value: Value to validate
            schema: Schema to validate against
            path: Path to the value
            errors: List to append errors to
        """
        schema_type = schema.get("type")
        
        # Check type
        if schema_type == "object" and isinstance(value, dict):
            self._validate_object(value, schema, path, errors)
        elif schema_type == "array" and isinstance(value, list):
            self._validate_array(value, schema, path, errors)
        elif schema_type == "string" and not isinstance(value, str):
            errors.append(ValidationError(path, "Expected string", value))
        elif schema_type == "number" and not isinstance(value, (int, float)):
            errors.append(ValidationError(path, "Expected number", value))
        elif schema_type == "integer" and not isinstance(value, int):
            errors.append(ValidationError(path, "Expected integer", value))
        elif schema_type == "boolean" and not isinstance(value, bool):
            errors.append(ValidationError(path, "Expected boolean", value))
        elif schema_type == "null" and value is not None:
            errors.append(ValidationError(path, "Expected null", value))
        
        # Check enum
        if "enum" in schema and value not in schema["enum"]:
            errors.append(ValidationError(
                path,
                f"Value must be one of {schema['enum']}",
                value
            ))
        
        # Check string constraints
        if schema_type == "string" and isinstance(value, str):
            if "minLength" in schema and len(value) < schema["minLength"]:
                errors.append(ValidationError(
                    path,
                    f"String length must be at least {schema['minLength']}",
                    value
                ))
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                errors.append(ValidationError(
                    path,
                    f"String length must be at most {schema['maxLength']}",
                    value
                ))
            if "pattern" in schema and not re.match(schema["pattern"], value):
                errors.append(ValidationError(
                    path,
                    f"String must match pattern {schema['pattern']}",
                    value
                ))
        
        # Check number constraints
        if schema_type in ("number", "integer") and isinstance(value, (int, float)):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(ValidationError(
                    path,
                    f"Value must be at least {schema['minimum']}",
                    value
                ))
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(ValidationError(
                    path,
                    f"Value must be at most {schema['maximum']}",
                    value
                ))
            if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
                errors.append(ValidationError(
                    path,
                    f"Value must be greater than {schema['exclusiveMinimum']}",
                    value
                ))
            if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
                errors.append(ValidationError(
                    path,
                    f"Value must be less than {schema['exclusiveMaximum']}",
                    value
                ))
            if "multipleOf" in schema and value % schema["multipleOf"] != 0:
                errors.append(ValidationError(
                    path,
                    f"Value must be a multiple of {schema['multipleOf']}",
                    value
                ))
    
    def _validate_array(self, array: List[Any], schema: Dict[str, Any], path: str, errors: List[ValidationError]) -> None:
        """Validate an array against a schema.
        
        Args:
            array: Array to validate
            schema: Schema to validate against
            path: Path to the array
            errors: List to append errors to
        """
        # Check length constraints
        if "minItems" in schema and len(array) < schema["minItems"]:
            errors.append(ValidationError(
                path,
                f"Array length must be at least {schema['minItems']}",
                array
            ))
        if "maxItems" in schema and len(array) > schema["maxItems"]:
            errors.append(ValidationError(
                path,
                f"Array length must be at most {schema['maxItems']}",
                array
            ))
        
        # Check uniqueness
        if schema.get("uniqueItems", False) and len(array) != len(set(array)):
            errors.append(ValidationError(
                path,
                "Array items must be unique",
                array
            ))
        
        # Check items
        if "items" in schema:
            items_schema = schema["items"]
            if isinstance(items_schema, dict):
                # Same schema for all items
                for i, item in enumerate(array):
                    item_path = f"{path}[{i}]"
                    self._validate_value(item, items_schema, item_path, errors)
            elif isinstance(items_schema, list):
                # Different schema for each item
                for i, item in enumerate(array):
                    if i < len(items_schema):
                        item_path = f"{path}[{i}]"
                        self._validate_value(item, items_schema[i], item_path, errors)
        
        # Check additional items
        additional_items = schema.get("additionalItems", True)
        if additional_items is False and isinstance(schema.get("items"), list):
            if len(array) > len(schema["items"]):
                errors.append(ValidationError(
                    path,
                    f"Array length must be at most {len(schema['items'])}",
                    array
                ))
        elif additional_items is not True and isinstance(schema.get("items"), list):
            for i, item in enumerate(array):
                if i >= len(schema["items"]):
                    item_path = f"{path}[{i}]"
                    self._validate_value(item, additional_items, item_path, errors)
    
    def get_default(self) -> Dict[str, Any]:
        """Get default configuration values.
        
        Returns:
            Default configuration
        """
        result = {}
        properties = self.schema.get("properties", {})
        
        for name, prop_schema in properties.items():
            if "default" in prop_schema:
                result[name] = prop_schema["default"]
            elif prop_schema.get("type") == "object":
                if "properties" in prop_schema:
                    nested_schema = JsonSchema(prop_schema)
                    result[name] = nested_schema.get_default()
        
        return result
    
    def parse(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and convert configuration to a typed object.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Typed configuration object
        """
        # This implementation just returns the input dictionary
        # For more advanced parsing, you could convert to specific types
        return config


class DataclassSchema(ConfigSchema[T]):
    """Dataclass-based schema implementation."""
    
    def __init__(self, dataclass_type: Type[T]):
        """Initialize dataclass schema.
        
        Args:
            dataclass_type: Dataclass type
        """
        if not is_dataclass(dataclass_type):
            raise TypeError(f"{dataclass_type.__name__} is not a dataclass")
        
        self.dataclass_type = dataclass_type
        self._fields = {}
        
        # Extract field information
        for name, field_info in dataclass_type.__dataclass_fields__.items():
            required = field_info.default is field_info.default_factory is None
            default = field_info.default if field_info.default is not field_info.default_factory else None
            
            # Get validators from field metadata
            validators = field_info.metadata.get("validators", [])
            
            # Get description from field metadata or docstring
            description = field_info.metadata.get("description", "")
            
            self._fields[name] = SchemaField(
                name=name,
                type=field_info.type,
                required=required,
                default=default,
                description=description,
                validators=validators
            )
    
    def validate(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration against the schema.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Validation result
        """
        errors = []
        
        # Check required fields
        for name, field in self._fields.items():
            if field.required and name not in config:
                errors.append(ValidationError(
                    name,
                    f"Required field '{name}' is missing"
                ))
        
        # Validate field values
        for name, value in config.items():
            if name in self._fields:
                field = self._fields[name]
                error = field.validate(value)
                if error:
                    errors.append(ValidationError(name, error, value))
            else:
                errors.append(ValidationError(
                    name,
                    f"Unknown field '{name}'"
                ))
        
        return ValidationResult(not errors, errors)
    
    def get_default(self) -> Dict[str, Any]:
        """Get default configuration values.
        
        Returns:
            Default configuration
        """
        result = {}
        
        for name, field in self._fields.items():
            if field.default is not None:
                result[name] = field.default
        
        return result
    
    def parse(self, config: Dict[str, Any]) -> T:
        """Parse and convert configuration to a typed object.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Typed configuration object
        """
        # Create an instance of the dataclass
        instance = self.dataclass_type(**config)
        return instance


class SchemaRegistry:
    """Registry for configuration schemas."""
    
    def __init__(self):
        """Initialize schema registry."""
        self._schemas: Dict[str, ConfigSchema] = {}
    
    def register(self, name: str, schema: ConfigSchema) -> None:
        """Register a schema.
        
        Args:
            name: Schema name
            schema: Schema instance
        """
        self._schemas[name] = schema
    
    def get(self, name: str) -> Optional[ConfigSchema]:
        """Get a schema by name.
        
        Args:
            name: Schema name
            
        Returns:
            Schema instance or None if not found
        """
        return self._schemas.get(name)
    
    def has(self, name: str) -> bool:
        """Check if a schema exists.
        
        Args:
            name: Schema name
            
        Returns:
            True if schema exists, False otherwise
        """
        return name in self._schemas
    
    def remove(self, name: str) -> None:
        """Remove a schema.
        
        Args:
            name: Schema name
        """
        if name in self._schemas:
            del self._schemas[name]
    
    def get_all(self) -> Dict[str, ConfigSchema]:
        """Get all registered schemas.
        
        Returns:
            Dictionary of schema names to schema instances
        """
        return self._schemas.copy()


# Singleton schema registry
_schema_registry = SchemaRegistry()

def get_schema_registry() -> SchemaRegistry:
    """Get the schema registry.
    
    Returns:
        Schema registry
    """
    return _schema_registry


# Common validators
def range_validator(min_value: Optional[float] = None, max_value: Optional[float] = None) -> Callable[[Any], Optional[str]]:
    """Create a validator for numeric ranges.
    
    Args:
        min_value: Minimum value (inclusive)
        max_value: Maximum value (inclusive)
        
    Returns:
        Validator function
    """
    def validator(value: Any) -> Optional[str]:
        if not isinstance(value, (int, float)):
            return f"Expected a number, got {type(value).__name__}"
        
        if min_value is not None and value < min_value:
            return f"Value must be at least {min_value}"
        
        if max_value is not None and value > max_value:
            return f"Value must be at most {max_value}"
        
        return None
    
    return validator


def length_validator(min_length: Optional[int] = None, max_length: Optional[int] = None) -> Callable[[Any], Optional[str]]:
    """Create a validator for string/list/dict lengths.
    
    Args:
        min_length: Minimum length (inclusive)
        max_length: Maximum length (inclusive)
        
    Returns:
        Validator function
    """
    def validator(value: Any) -> Optional[str]:
        if not hasattr(value, "__len__"):
            return f"Expected a sized object, got {type(value).__name__}"
        
        if min_length is not None and len(value) < min_length:
            return f"Length must be at least {min_length}"
        
        if max_length is not None and len(value) > max_length:
            return f"Length must be at most {max_length}"
        
        return None
    
    return validator


def pattern_validator(pattern: str) -> Callable[[Any], Optional[str]]:
    """Create a validator for string patterns.
    
    Args:
        pattern: Regular expression pattern
        
    Returns:
        Validator function
    """
    compiled = re.compile(pattern)
    
    def validator(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return f"Expected a string, got {type(value).__name__}"
        
        if not compiled.match(value):
            return f"String must match pattern {pattern}"
        
        return None
    
    return validator


def enum_validator(values: List[Any]) -> Callable[[Any], Optional[str]]:
    """Create a validator for enum values.
    
    Args:
        values: List of allowed values
        
    Returns:
        Validator function
    """
    def validator(value: Any) -> Optional[str]:
        if value not in values:
            return f"Value must be one of {values}"
        
        return None
    
    return validator


def type_validator(expected_type: Type) -> Callable[[Any], Optional[str]]:
    """Create a validator for types.
    
    Args:
        expected_type: Expected type
        
    Returns:
        Validator function
    """
    def validator(value: Any) -> Optional[str]:
        if not isinstance(value, expected_type):
            return f"Expected {expected_type.__name__}, got {type(value).__name__}"
        
        return None
    
    return validator
