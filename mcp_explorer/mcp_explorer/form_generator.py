"""Dynamic form generation from JSON schemas."""
from typing import Dict, Any, List, Union
from pydantic import BaseModel, create_model
from textual.widgets import Input, Label, Checkbox, Select
from textual.containers import Vertical
from textual import on
from textual.events import Paste
import pyperclip


class PasteableInput(Input):
    """An Input widget with proper text handling for terminal applications."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def on_paste(self, event: "Paste") -> None:
        """Handle paste events."""
        # Insert the pasted text at the current cursor position
        cursor_pos = self.cursor_position
        current_value = self.value
        new_value = current_value[:cursor_pos] + event.text + current_value[cursor_pos:]
        self.value = new_value
        # Move cursor to end of pasted text
        self.cursor_position = cursor_pos + len(event.text)
        # Stop the event from bubbling up
        event.stop()
    
    def on_focus(self) -> None:
        """Called when the widget gains focus."""
        # Ensure the widget is ready to receive paste events
        self.can_focus = True


class SchemaFormGenerator:
    """Generates TUI forms dynamically from JSON schemas."""
    
    @staticmethod
    def generate_form_fields(schema: Dict[str, Any], form_id_prefix: str = "field"):
        """Generate form widgets based on the provided JSON schema."""
        widgets = []
        
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])
        
        for prop_name, prop_details in properties.items():
            field_type = prop_details.get("type", "string")
            description = prop_details.get("description", "")
            title = prop_details.get("title", prop_name)
            
            # Add label
            required_indicator = "*" if prop_name in required_fields else ""
            label = Label(f"{title}{required_indicator}: {description}")
            widgets.append(label)
            
            # Create appropriate input widget based on type
            field_widget = SchemaFormGenerator._create_widget(
                field_type, 
                prop_details, 
                f"{form_id_prefix}-{prop_name}"
            )
            widgets.append(field_widget)
        
        return widgets
    
    @staticmethod
    def _create_widget(field_type: str, prop_details: Dict[str, Any], widget_id: str):
        """Create an appropriate widget based on the field type."""
        if field_type == "boolean":
            return Checkbox(label="", id=widget_id)
        elif field_type == "integer" or field_type == "number":
            input_widget = PasteableInput(
                placeholder=prop_details.get("description", ""),
                id=widget_id,
                type="integer" if field_type == "integer" else "number"
            )
            # Set min/max if specified
            if "minimum" in prop_details:
                input_widget.placeholder += f" (min: {prop_details['minimum']})"
            if "maximum" in prop_details:
                input_widget.placeholder += f" (max: {prop_details['maximum']})"
            return input_widget
        elif field_type == "array":
            # For arrays, we'll create a text input expecting JSON
            return PasteableInput(
                placeholder=f"Enter JSON array: {prop_details.get('description', '')}",
                id=widget_id,
                type="text"
            )
        elif field_type == "object":
            # For objects, we'll create a text input expecting JSON
            return PasteableInput(
                placeholder=f"Enter JSON object: {prop_details.get('description', '')}",
                id=widget_id,
                type="text"
            )
        else:  # string, or any other type
            # Check if there are enum values
            if "enum" in prop_details:
                options = [(str(val), str(val)) for val in prop_details["enum"]]
                return Select(options, id=widget_id)
            else:
                return PasteableInput(
                    placeholder=prop_details.get("description", ""),
                    id=widget_id,
                    type="text"
                )
    
    @staticmethod
    def collect_form_values(widgets: List, schema: Dict[str, Any], form_id_prefix: str = "field"):
        """Collect values from form widgets based on the schema."""
        values = {}
        
        properties = schema.get("properties", {})
        
        for prop_name, prop_details in properties.items():
            widget_id = f"{form_id_prefix}-{prop_name}"
            
            # Find the widget by ID
            widget = None
            for w in widgets:
                if hasattr(w, 'id') and w.id == widget_id:
                    widget = w
                    break
            
            if widget is not None:
                # Extract value based on widget type
                if isinstance(widget, Checkbox):
                    values[prop_name] = widget.value
                elif isinstance(widget, Select):
                    values[prop_name] = widget.value
                else:  # Input widget
                    value = widget.value.strip()
                    
                    # Convert to appropriate type based on schema
                    field_type = prop_details.get("type", "string")
                    if field_type == "boolean" and value.lower() in ("true", "false"):
                        values[prop_name] = value.lower() == "true"
                    elif field_type == "integer" and value:
                        try:
                            values[prop_name] = int(value)
                        except ValueError:
                            values[prop_name] = value  # Keep as string if conversion fails
                    elif field_type == "number" and value:
                        try:
                            values[prop_name] = float(value)
                        except ValueError:
                            values[prop_name] = value  # Keep as string if conversion fails
                    elif field_type == "array" and value:
                        try:
                            # Expecting JSON array
                            import json
                            values[prop_name] = json.loads(value)
                        except json.JSONDecodeError:
                            values[prop_name] = value  # Keep as string if JSON parsing fails
                    elif field_type == "object" and value:
                        try:
                            # Expecting JSON object
                            import json
                            values[prop_name] = json.loads(value)
                        except json.JSONDecodeError:
                            values[prop_name] = value  # Keep as string if JSON parsing fails
                    else:
                        values[prop_name] = value
        
        return values
    
    @staticmethod
    def validate_against_schema(values: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate collected values against the schema."""
        errors = []
        
        # Check required fields
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in values or values[field] == "":
                errors.append(f"Required field '{field}' is missing or empty")
        
        # Basic type validation
        properties = schema.get("properties", {})
        for field_name, field_value in values.items():
            if field_name in properties:
                expected_type = properties[field_name].get("type")
                
                if expected_type == "integer" and not isinstance(field_value, int):
                    try:
                        values[field_name] = int(field_value)
                    except (ValueError, TypeError):
                        errors.append(f"Field '{field_name}' should be an integer")
                        
                elif expected_type == "number" and not isinstance(field_value, (int, float)):
                    try:
                        values[field_name] = float(field_value)
                    except (ValueError, TypeError):
                        errors.append(f"Field '{field_name}' should be a number")
                        
                elif expected_type == "boolean" and not isinstance(field_value, bool):
                    if isinstance(field_value, str):
                        if field_value.lower() in ("true", "false"):
                            values[field_name] = field_value.lower() == "true"
                        else:
                            errors.append(f"Field '{field_name}' should be a boolean (true/false)")
                    else:
                        errors.append(f"Field '{field_name}' should be a boolean")
        
        return len(errors) == 0, errors