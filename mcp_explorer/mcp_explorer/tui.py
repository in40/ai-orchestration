"""TUI for MCP Explorer using textual library."""
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Tree, DataTable, Static,
    Button, Input, Label, Checkbox, Select
)
from textual.screen import ModalScreen, Screen
from textual import on
from textual.events import Paste
from textual.message import Message
from .registry_adapters import RegistryManager
from .streamable_http import StreamableHTTPClient
from .form_generator import SchemaFormGenerator
from typing import Dict, Any, List, Optional
import asyncio
import urllib.parse


class ConnectionErrorScreen(Screen):
    """Screen shown when registry connection fails."""
    
    def __init__(self, registry_manager: RegistryManager):
        super().__init__()
        self.registry_manager = registry_manager
    
    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="connection-error-container"):
            yield Static(
                "🚫 REGISTRY CONNECTION FAILED\n"
                "Default registry at http://localhost:3031\n"
                "is not responding or is not Streamable HTTP.\n\n",
                id="error-message"
            )
            with Horizontal(id="error-buttons"):
                yield Button("F2 Add Custom Registry", id="add-registry-btn", variant="primary")
                yield Button("F8 Quit", id="quit-btn", variant="error")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-registry-btn":
            self.app.push_screen(AddRegistryScreen(self.registry_manager))
        elif event.button.id == "quit-btn":
            self.app.exit()


class AddRegistryScreen(ModalScreen):
    """Modal screen for adding custom registries."""
    
    def __init__(self, registry_manager: RegistryManager):
        super().__init__()
        self.registry_manager = registry_manager
    
    def compose(self) -> ComposeResult:
        with Container(id="add-registry-modal"):
            yield Static("Add Custom Registry", id="modal-title")
            yield Label("Registry Name:")
            yield Input(placeholder="e.g., My Custom Registry", id="registry-name")
            yield Label("Registry URL:")
            yield Input(placeholder="e.g., https://my-registry.com/api", id="registry-url")
            yield Label("Registry Type:")
            yield Input(placeholder="github, nacos, or custom", id="registry-type")
            with Horizontal(id="modal-buttons"):
                yield Button("Add", id="add-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="warning")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            name = self.query_one("#registry-name").value
            url = self.query_one("#registry-url").value
            reg_type = self.query_one("#registry-type").value
            
            # Add the registry based on type
            if reg_type == "github":
                from .registry_adapters import GitHubRegistryAdapter
                adapter = GitHubRegistryAdapter(base_url=url)
            elif reg_type == "nacos":
                from .registry_adapters import NacosRegistryAdapter
                adapter = NacosRegistryAdapter(base_url=url)
            else:
                from .registry_adapters import CustomRegistryAdapter
                adapter = CustomRegistryAdapter(base_url=url)
                
            self.registry_manager.add_adapter(adapter)
            self.app.pop_screen()
        elif event.button.id == "cancel-btn":
            self.app.pop_screen()


class ToolFormScreen(ModalScreen):
    """Modal screen for tool parameter input."""

    def __init__(self, tool_schema: Dict[str, Any], tool_name: str, server_url: str):
        super().__init__()
        self.tool_schema = tool_schema
        self.tool_name = tool_name
        self.server_url = server_url
        # Ensure input_schema is a dict to prevent errors in form generation
        self.input_schema = tool_schema.get("inputSchema", {}) or {}
        self.form_widgets = []
        self.results_display = None
        
        # Sanitize the tool name for use in form ID prefixes to ensure valid widget IDs
        self.sanitized_tool_name_for_ids = tool_name.replace(':', '_').replace('.', '_').replace('/', '_')

    def compose(self) -> ComposeResult:
        with Container(id="tool-form-modal"):
            yield Static(f"Tool: {self.tool_name}", id="tool-title")

            try:
                # Generate form fields based on schema using the form generator
                # Use the sanitized tool name to ensure valid widget IDs
                self.form_widgets = SchemaFormGenerator.generate_form_fields(
                    self.input_schema,
                    f"field-{self.sanitized_tool_name_for_ids}"
                )

                for widget in self.form_widgets:
                    yield widget
            except Exception as e:
                # If form generation fails, show an error message instead
                yield Static(f"[red]Error generating form: {str(e)}[/red]", id="form-error")

            # Add a scrollable area for displaying results
            with Container(id="results-container-wrapper", classes="results-container"):
                # Add a label for the results section
                yield Static("Results:", id="results-label")
                # Use a larger scrollable container for results
                with ScrollableContainer(id="results-container", classes="results-scrollable"):
                    # Use a DataTable widget for better results display
                    self.results_display = DataTable(id="results-display")
                    self.results_display.can_focus = True
                    self.results_display.expand = True
                    self.results_display.shrink = False  # Don't shrink the table
                    yield self.results_display

            with Horizontal(id="form-buttons"):
                yield Button("F7 Call Tool", id="call-tool-btn", variant="success")
                yield Button("Clear Results", id="clear-results-btn", variant="default")
                yield Button("Close", id="close-btn", variant="warning")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "call-tool-btn":
            # Collect form values using the form generator
            arguments = SchemaFormGenerator.collect_form_values(
                self.form_widgets,
                self.input_schema,
                f"field-{self.sanitized_tool_name_for_ids}"
            )

            # Validate against schema
            is_valid, errors = SchemaFormGenerator.validate_against_schema(
                arguments,
                self.input_schema
            )

            if not is_valid:
                error_msg = "\n".join(errors)
                self.display_result(f"Validation errors:\n{error_msg}", is_error=True)
                return

            # Call the tool
            await self.call_tool_with_args(arguments)
        elif event.button.id == "clear-results-btn":
            # Clear the results display
            if self.results_display:
                self.results_display.clear()
                self.results_display.add_columns("Cleared")
                self.results_display.add_row("Results cleared. Run tool again to see output.")
        elif event.button.id == "close-btn":
            # Close the modal
            self.app.pop_screen()

    async def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key == "f7":
            # Trigger the call tool button when F7 is pressed
            await self.call_tool_action()
        elif event.key == "escape":
            # Close the modal when Escape is pressed
            self.app.pop_screen()
        elif event.key == "ctrl+c":
            # Copy selected cell content to clipboard
            await self.copy_selected_cell()
    
    async def copy_selected_cell(self):
        """Copy the currently selected cell to clipboard."""
        try:
            if self.results_display.cursor_row is not None and self.results_display.cursor_column is not None:
                # Get the value from the currently selected cell
                row_index = self.results_display.cursor_row
                col_index = self.results_display.cursor_column
                
                # Get the column key from the index
                column_keys = list(self.results_display.columns.keys())
                if col_index < len(column_keys):
                    column_key = column_keys[col_index]
                    
                    # Get the row key from the index
                    row_keys = list(self.results_display.rows.keys())
                    if row_index < len(row_keys):
                        row_key = row_keys[row_index]
                        
                        # Get the value from the table
                        value = self.results_display.get_cell(row_key, column_key)
                        
                        # Copy to clipboard - using pyperclip or similar
                        try:
                            import pyperclip
                            pyperclip.copy(str(value))
                        except ImportError:
                            # If pyperclip is not available, try using tkinter
                            try:
                                import tkinter as tk
                                root = tk.Tk()
                                root.withdraw()
                                root.clipboard_clear()
                                root.clipboard_append(str(value))
                                root.destroy()
                            except ImportError:
                                # If neither is available, just store in a variable
                                self.app.clipboard_content = str(value)
                        self.app.notify(f"Copied to clipboard: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}", 
                                      severity="information")
                    else:
                        self.app.notify("No row selected", severity="warning")
                else:
                    self.app.notify("No column selected", severity="warning")
            else:
                self.app.notify("No cell selected", severity="warning")
        except Exception as e:
            self.app.notify(f"Error copying to clipboard: {str(e)}", severity="error")
    
    def on_paste(self, event: "Paste") -> None:
        """Handle paste events in the form screen."""
        # Forward paste events to focused input if any
        if self.focus_chain:
            focused_widget = self.focused
            if focused_widget and hasattr(focused_widget, 'on_paste'):
                # Call the widget's paste handler directly
                focused_widget.on_paste(event)

    async def call_tool_action(self):
        """Execute the tool call action."""
        # Collect form values using the form generator
        arguments = SchemaFormGenerator.collect_form_values(
            self.form_widgets,
            self.input_schema,
            f"field-{self.sanitized_tool_name_for_ids}"
        )

        # Validate against schema
        is_valid, errors = SchemaFormGenerator.validate_against_schema(
            arguments,
            self.input_schema
        )

        if not is_valid:
            error_msg = "\n".join(errors)
            self.app.notify(f"Validation errors:\n{error_msg}", severity="error")
            return

        # Call the tool
        await self.call_tool_with_args(arguments)
    
    async def call_tool_with_args(self, arguments: Dict[str, Any]):
        """Call the tool with collected arguments."""
        try:
            # Notify user that tool is being called
            self.app.notify("Calling tool...", severity="information")
            
            # Use the app's centralized method to call the capability
            result = await self.app.call_capability_on_server("tool", self.tool_schema, self.server_url, arguments)

            # Display result in the form instead of notification
            if "error" not in result:
                # Pass the actual result object to preserve structure
                self.display_result(result, is_error=False)
                
                # Always notify the user that the tool was executed, regardless of result content
                # Extract important information from the result if available
                result_summary = "Tool executed successfully"
                
                # Look for common result indicators like task IDs
                if isinstance(result, dict):
                    if 'result' in result and isinstance(result['result'], dict):
                        # Check for task ID or similar identifier
                        task_id = result['result'].get('id') or result['result'].get('taskId') or result['result'].get('jobId')
                        if task_id:
                            result_summary = f"Tool executed successfully. Task ID: {task_id}"
                    elif 'result' in result and isinstance(result['result'], list) and len(result['result']) > 0:
                        result_summary = f"Tool executed successfully. Returned {len(result['result'])} items."
                    elif result != {}:
                        result_summary = "Tool executed successfully. See results below."
                
                self.app.notify(result_summary, severity="success")
                
                # Ensure the results area is scrolled to show the new content
                # and bring attention to it
                self.results_display.scroll_visible(top=True)
            else:
                error_text = f"Tool execution failed:\n{result['error']}"
                self.display_result(error_text, is_error=True)
                self.app.notify(f"Tool execution failed: {result['error']}", severity="error")
        except Exception as e:
            error_text = f"Error calling tool:\n{str(e)}"
            self.display_result(error_text, is_error=True)
            self.app.notify(f"Error calling tool: {str(e)}", severity="error")

        # Keep the form open for additional submissions
        # self.app.pop_screen() - removed this line

    def display_result(self, result_data, is_error: bool = False):
        """Display the result in the results area."""
        if self.results_display:
            try:
                import json

                # Clear the existing table
                self.results_display.clear()

                # Handle different types of result data
                if isinstance(result_data, dict):
                    # If it's an error response
                    if is_error:
                        self.results_display.add_columns("Error")
                        self.results_display.add_row(json.dumps(result_data, indent=2))
                        # Force refresh of the widget
                        self.results_display.refresh()
                        return

                    # Check if it's a structured response with a 'result' field
                    if 'result' in result_data:
                        actual_result = result_data['result']

                        # Check if there are other important fields alongside 'result' (like task ID)
                        additional_fields = {k: v for k, v in result_data.items() if k != 'result'}
                        
                        # If there are additional fields, display them first
                        if additional_fields:
                            # Add columns if none exist
                            if len(self.results_display.columns) == 0:
                                self.results_display.add_columns("Field", "Value")
                            
                            for key, value in additional_fields.items():
                                if isinstance(value, (dict, list)):
                                    value = json.dumps(value, indent=2)
                                self.results_display.add_row(str(key), str(value))

                            # Add a separator
                            self.results_display.add_row("---", "---")

                            # Then add the main result
                            if isinstance(actual_result, list):
                                # If it's a list (like tasks), render as a table
                                self.render_list_as_table(actual_result)
                            elif isinstance(actual_result, dict):
                                # If it's a dict, check for special cases first
                                if 'tasks' in actual_result:
                                    # Special handling for tasks list
                                    tasks = actual_result['tasks']
                                    if isinstance(tasks, list):
                                        self.render_list_as_table(tasks)
                                    else:
                                        # If tasks is not a list, render as dict
                                        self.render_dict_as_table(actual_result)
                                elif 'tools' in actual_result:
                                    # Special handling for tools list
                                    tools = actual_result['tools']
                                    if isinstance(tools, list):
                                        self.render_list_as_table(tools)
                                    else:
                                        # If tools is not a list, render as dict
                                        self.render_dict_as_table(actual_result)
                                elif 'resources' in actual_result:
                                    # Special handling for resources list
                                    resources = actual_result['resources']
                                    if isinstance(resources, list):
                                        self.render_list_as_table(resources)
                                    else:
                                        # If resources is not a list, render as dict
                                        self.render_dict_as_table(actual_result)
                                else:
                                    # If it's a dict without special keys, render as key-value table
                                    self.render_dict_as_table(actual_result)
                            else:
                                # For other types, add as a row
                                if isinstance(actual_result, (dict, list)):
                                    actual_result = json.dumps(actual_result, indent=2)
                                self.results_display.add_row("Result", str(actual_result))
                        else:
                            # No additional fields, just process the result normally
                            if isinstance(actual_result, list):
                                # If it's a list (like tasks), render as a table
                                self.render_list_as_table(actual_result)
                            elif isinstance(actual_result, dict):
                                # If it's a dict, check for special cases first
                                if 'tasks' in actual_result:
                                    # Special handling for tasks list
                                    tasks = actual_result['tasks']
                                    if isinstance(tasks, list):
                                        self.render_list_as_table(tasks)
                                    else:
                                        # If tasks is not a list, render as dict
                                        self.render_dict_as_table(actual_result)
                                elif 'tools' in actual_result:
                                    # Special handling for tools list
                                    tools = actual_result['tools']
                                    if isinstance(tools, list):
                                        self.render_list_as_table(tools)
                                    else:
                                        # If tools is not a list, render as dict
                                        self.render_dict_as_table(actual_result)
                                elif 'resources' in actual_result:
                                    # Special handling for resources list
                                    resources = actual_result['resources']
                                    if isinstance(resources, list):
                                        self.render_list_as_table(resources)
                                    else:
                                        # If resources is not a list, render as dict
                                        self.render_dict_as_table(actual_result)
                                else:
                                    # If it's a dict without special keys, render as key-value table
                                    self.render_dict_as_table(actual_result)
                            else:
                                # For other types, display as formatted text
                                self.results_display.add_columns("Result")
                                self.results_display.add_row(json.dumps(actual_result, indent=2))
                    else:
                        # If it's a dict without a 'result' field, render as key-value table
                        self.render_dict_as_table(result_data)
                elif isinstance(result_data, list):
                    # If it's a list, render as a table
                    self.render_list_as_table(result_data)
                elif isinstance(result_data, str):
                    # If it's a string, check if it starts with "Tool Result:\n"
                    if result_data.startswith("Tool Result:\n"):
                        # Extract the actual result part after the prefix
                        actual_result_str = result_data[len("Tool Result:\n"):].strip()

                        # Try to parse the actual result as JSON
                        try:
                            parsed_result = json.loads(actual_result_str)
                            if isinstance(parsed_result, list):
                                self.render_list_as_table(parsed_result)
                            elif isinstance(parsed_result, dict):
                                # Check if it has a 'result' field inside
                                if 'result' in parsed_result:
                                    actual_result = parsed_result['result']
                                    if isinstance(actual_result, list):
                                        self.render_list_as_table(actual_result)
                                    elif isinstance(actual_result, dict):
                                        self.render_dict_as_table(actual_result)
                                    else:
                                        self.results_display.add_columns("Result")
                                        self.results_display.add_row(json.dumps(actual_result, indent=2))
                                else:
                                    self.render_dict_as_table(parsed_result)
                            else:
                                # For other types, display as formatted text
                                self.results_display.add_columns("Result")
                                self.results_display.add_row(json.dumps(parsed_result, indent=2))
                        except json.JSONDecodeError:
                            # If it's not JSON, display as plain text
                            self.results_display.add_columns("Result")
                            self.results_display.add_row(result_data)
                    else:
                        # If it's a plain string, display as formatted text
                        self.results_display.add_columns("Result")
                        self.results_display.add_row(result_data)
                else:
                    # For other types, display as formatted text
                    self.results_display.add_columns("Result")
                    self.results_display.add_row(json.dumps(result_data, indent=2))

                # Force refresh of the widget to ensure it's visible
                self.results_display.refresh()

            except Exception as e:
                # If anything goes wrong, fall back to the original behavior
                import json
                self.results_display.clear()
                self.results_display.add_columns("Error")
                self.results_display.add_row(f"Error displaying result: {str(e)}\n{json.dumps(result_data, indent=2)}")
                # Force refresh of the widget
                self.results_display.refresh()

    def render_list_as_table(self, data_list):
        """Render a list of items as a user-friendly table."""
        import json

        if not data_list:
            # Update the existing display with a message
            self.results_display.clear()
            self.results_display.add_columns("Message")
            self.results_display.add_row("No items found in the list.")
            return

        # Check if this looks like a job/task list (has common fields like taskId, status, etc.)
        # First, make sure data_list[0] exists and is a dict before accessing it
        if data_list and isinstance(data_list[0], dict):
            # Check for common job/task fields
            first_item = data_list[0]
            if any(field in first_item for field in ['taskId', 'jobId', 'id', 'task_id', 'job_id']):
                try:
                    # This looks like a job/task list, create a DataTable
                    self.render_job_list_as_table(data_list)
                    return
                except Exception as e:
                    # If there's an error in formatting, fall back to JSON
                    pass

        # For other types of lists, create a generic table
        self.create_generic_list_table(data_list)
    
    def render_job_list_as_table(self, job_list):
        """Render a job/task list as a DataTable."""
        # Determine the columns based on the first item
        if not job_list or not isinstance(job_list[0], dict):
            self.results_display.clear()
            self.results_display.add_columns("Data")
            self.results_display.add_row(str(job_list))
            return
        
        # Define priority columns that should appear first for tasks/jobs
        priority_cols = ['id', 'taskId', 'task_id', 'jobId', 'job_id', 'status', 'name', 'description', 'state']
        
        # Collect all unique keys from all items to create columns
        all_keys = set()
        for job in job_list:
            if isinstance(job, dict):
                all_keys.update(job.keys())
        
        # Separate priority columns from others
        priority_keys = []
        other_keys = []
        for key in sorted(list(all_keys)):
            if key.lower() in [col.lower() for col in priority_cols]:
                priority_keys.append(key)
            else:
                other_keys.append(key)
        
        # Combine priority keys first, then others
        sorted_keys = priority_keys + other_keys
        
        # Add columns to the table
        self.results_display.clear()
        self.results_display.add_columns(*sorted_keys)
        
        # Add rows to the table
        for job in job_list:
            if isinstance(job, dict):
                # Create a row with values for each column
                row = []
                for key in sorted_keys:
                    value = job.get(key, "")
                    # Convert complex objects to JSON strings for display
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, indent=2)
                    row.append(str(value))
                self.results_display.add_row(*row)
            else:
                # If the item is not a dict, just add it as a single cell
                self.results_display.add_row(str(job))
    
    
    def create_generic_list_table(self, data_list):
        """Create a generic table for any list data."""
        import json
        
        # If the list contains dictionaries, try to make a nice table
        if data_list and all(isinstance(item, dict) for item in data_list):
            # Collect all unique keys from all items to create columns
            all_keys = set()
            for item in data_list:
                all_keys.update(item.keys())
            
            # Sort keys to have consistent column ordering
            sorted_keys = sorted(list(all_keys))
            
            # Add columns to the table
            self.results_display.clear()
            self.results_display.add_columns(*sorted_keys)
            
            # Add rows to the table
            for item in data_list:
                row = []
                for key in sorted_keys:
                    value = item.get(key, "")
                    # Convert complex objects to JSON strings for display
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value, indent=2)
                    row.append(str(value))
                self.results_display.add_row(*row)
        else:
            # For mixed or non-dict lists, create a simple index/value table
            self.results_display.clear()
            self.results_display.add_columns("Index", "Value")
            for i, item in enumerate(data_list):
                value = item
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, indent=2)
                self.results_display.add_row(str(i), str(value))
    
    def format_job_list(self, job_list):
        """Format a job list in a user-friendly way."""
        result_lines = ["Job List:", "="*50]
        
        for i, job in enumerate(job_list):
            if isinstance(job, dict):
                job_id = job.get('taskId', job.get('id', job.get('jobId', f'Job #{i+1}')))
                status = job.get('status', 'unknown')
                description = job.get('description', job.get('name', 'No description'))
                
                result_lines.append(f"ID: {job_id}")
                result_lines.append(f"Status: {status}")
                result_lines.append(f"Description: {description}")
                
                # Add other important fields if present
                for key, value in job.items():
                    if key not in ['taskId', 'id', 'jobId', 'status', 'description', 'name']:
                        result_lines.append(f"  {key}: {value}")
                
                result_lines.append("-" * 30)
            else:
                result_lines.append(str(job))
                result_lines.append("-" * 30)
        
        return "\n".join(result_lines)

    def render_dict_as_table(self, data_dict):
        """Render a dictionary as a key-value table."""
        import json

        if not data_dict:
            # Update the existing display with a message
            self.results_display.clear()
            self.results_display.add_columns("Message")
            self.results_display.add_row("Dictionary is empty.")
            return

        # Create a key-value table for the dictionary
        self.results_display.clear()
        self.results_display.add_columns("Key", "Value")
        
        for key, value in data_dict.items():
            # Convert complex objects to JSON strings for display
            if isinstance(value, (dict, list)):
                value = json.dumps(value, indent=2)
            self.results_display.add_row(str(key), str(value))

    async def copy_cell_to_clipboard(self, event):
        """Copy the content of the selected cell to clipboard."""
        try:
            # Get the selected row and column
            row_key = event.row_key.value
            column_key = event.column_key.value

            # Get the value from the table
            table = event.sender
            value = table.get_cell_at(row_key, column_key)

            # Use Textual's built-in clipboard functionality which uses OSC 52
            await self.app.copy_to_clipboard(str(value))
            self.app.notify(f"Copied to clipboard: {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}", severity="information")

        except Exception as e:
            # If OSC 52 fails, try alternative methods
            try:
                # Try using pyperclip as a fallback
                import pyperclip
                pyperclip.copy(str(value))
                self.app.notify(f"Copied to clipboard (fallback): {str(value)[:50]}{'...' if len(str(value)) > 50 else ''}", severity="information")
            except ImportError:
                # If pyperclip is not available, just show the error from OSC 52
                self.app.notify(f"Error copying to clipboard: {str(e)}", severity="error")
            except Exception as pyperclip_error:
                # If pyperclip fails, show the original error
                self.app.notify(f"Error copying to clipboard: {str(e)}", severity="error")


class MCPExplorerApp(App):
    """Main MCP Explorer TUI Application."""

    TITLE = "MCP Explorer"
    SUB_TITLE = "Model Context Protocol Explorer (Streamable HTTP)"
    CSS_PATH = "mcp_explorer.tcss"

    def __init__(self, expand_all_by_default=True):
        super().__init__()
        self.registry_manager = RegistryManager()
        self.current_server = None
        self.current_server_url = None
        self.current_tools = []
        self.current_resources = []
        self.current_prompts = []
        self.expand_all_by_default = expand_all_by_default
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Horizontal(
            Vertical(
                Static("Infrastructure", id="infrastructure-header"),
                Tree("Registry", id="infrastructure-tree"),
                id="left-panel"
            ),
            Vertical(
                Static("Details", id="details-header"),
                DataTable(id="details-table"),
                id="right-panel"
            ),
            id="main-layout"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.call_later(self.load_infrastructure)

    async def load_infrastructure(self) -> None:
        """Load registries and populate the infrastructure tree."""
        try:
            servers = await self.registry_manager.search_all_servers()

            if not servers:
                # Show connection error screen if no servers found
                self.call_after_refresh(lambda: self.push_screen(ConnectionErrorScreen(self.registry_manager)))
                return

            # Populate the infrastructure tree - use call_after_refresh to ensure UI updates happen after render
            infra_tree = self.query_one("#infrastructure-tree", Tree)
            infra_tree.clear()

            # Add a root registry node
            root_node = infra_tree.root
            for server in servers:
                server_node = root_node.add(server["name"], data={"type": "server", "info": server})
                
                # Add capability nodes under each server
                tools_node = server_node.add("Tools", data={"type": "capability", "capability": "tools", "server_info": server})
                resources_node = server_node.add("Resources", data={"type": "capability", "capability": "resources", "server_info": server})
                prompts_node = server_node.add("Prompts", data={"type": "capability", "capability": "prompts", "server_info": server})
                
                # Expand nodes based on the setting
                if self.expand_all_by_default:
                    server_node.expand()
                    # Pre-populate and expand capability nodes to show all items
                    await self.pre_populate_and_expand_capabilities(server_node, server["url"])

        except Exception as e:
            self.call_after_refresh(lambda: self.notify(f"Error loading infrastructure: {str(e)}", severity="error"))

    async def pre_populate_and_expand_capabilities(self, server_node, server_url: str):
        """Pre-populate and expand capability nodes to show all items."""
        for capability_node in server_node.children:
            if capability_node.data and capability_node.data.get("type") == "capability":
                capability = capability_node.data["capability"]
                
                # Populate the capability node with its items
                await self.populate_capability_children(capability_node, capability, server_url)
                
                # Expand the capability node to show all items
                capability_node.expand()
    
    async def populate_capability_children(self, capability_node, capability: str, server_url: str) -> None:
        """Populate children nodes for a capability node with individual items."""
        try:
            client = StreamableHTTPClient(server_url)
            await client.connect()

            # Initialize the connection
            init_response = await client.initialize()
            await client.initialized(init_response.get("result", {}))

            items_list = []
            if capability == "tools":
                response = await client.list_tools()
                items_list = response.get("result", {}).get("tools", [])
            elif capability == "resources":
                response = await client.list_resources()
                items_list = response.get("result", {}).get("resources", [])
            elif capability == "prompts":
                try:
                    response = await client.send_request("prompts/list")
                    items_list = response.get("result", {}).get("prompts", [])
                except:
                    items_list = []

            # Add each item as a child node
            for item in items_list:
                item_name = item.get("name", "unnamed")
                item_description = item.get("description", "No description")
                
                # Add the item as a child node with appropriate data
                child_node = capability_node.add(f"{item_name}: {item_description[:50]}...", 
                                               data={
                                                   "type": "capability_item", 
                                                   "capability": capability,
                                                   "item": item,
                                                   "server_url": server_url
                                               })

            await client.close()

        except Exception as e:
            self.notify(f"Failed to load {capability} children: {str(e)}", severity="error")

    async def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle selection of a node in the infrastructure tree."""
        selected_node = event.node
        if selected_node.data:
            node_data = selected_node.data
            node_type = node_data.get("type")
            
            if node_type == "server":
                # Connect to the server and load all its capabilities
                server_info = node_data["info"]
                await self.connect_to_server(server_info["url"], server_info["name"])
            elif node_type == "capability":
                # Load specific capability items (tools, resources, or prompts) and add them as children
                capability = node_data["capability"]
                server_info = node_data["server_info"]
                
                # If the node has no children yet, fetch and add them
                if not selected_node.children:
                    await self.populate_capability_children(selected_node, capability, server_info["url"])
                
                # Expand the node to show children
                selected_node.expand()
                
                # Update the details panel to show the items
                await self.load_capability_items(capability, server_info["url"], server_info["name"])
            elif node_type == "capability_item":
                # Handle selection of individual capability items
                item = node_data["item"]
                capability = node_data["capability"]
                server_url = node_data["server_url"]
                
                # Update the details panel to show information about this specific item
                self.update_details_for_single_item(capability, item)
                
                # For executable capabilities, allow direct execution
                if capability == "tools":
                    # Show tool form for parameter input
                    self.show_tool_form(item, server_url)
                elif capability == "resources":
                    # Directly call the resource read capability
                    await self.call_resource_directly(item, server_url)
    
    async def call_capability_on_server(self, capability: str, item: Dict[str, Any], server_url: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a capability on a server."""
        try:
            # Notify about starting the connection
            self.notify(f"Connecting to server: {server_url}", severity="information")
            
            client = StreamableHTTPClient(server_url)
            await client.connect()

            # Initialize the connection if not already done
            if not hasattr(self, '_initialized_servers'):
                self._initialized_servers = set()

            if server_url not in self._initialized_servers:
                self.notify("Initializing connection...", severity="information")
                init_response = await client.initialize()
                await client.initialized(init_response.get("result", {}))
                self._initialized_servers.add(server_url)
                self.notify("Connection initialized", severity="information")

            result = None
            if capability == "tool":
                # Call the tool with arguments - extract the actual tool name from the canonical name
                # The item passed in might be the tool schema, so get the name from it
                tool_name = item.get("name", "")
                # If the tool_name is empty, try to extract from the item itself
                if not tool_name and hasattr(item, 'get'):
                    # If item is the schema dictionary, get name from it
                    tool_name = item.get("name", "")

                self.notify(f"Calling tool: {tool_name}", severity="information")
                result = await client.call_tool(tool_name, arguments or {})
                self.notify(f"Tool call completed, received result: {type(result).__name__}", severity="information")
            elif capability == "resource":
                # Read the resource
                resource_uri = item.get("uri", "")
                result = await client.read_resource(resource_uri)
            elif capability == "prompt":
                # For prompts, we might need a different approach depending on server implementation
                # This is a placeholder for now
                result = {"error": "Prompt execution not yet implemented"}

            await client.close()
            self.notify("Server connection closed", severity="information")
            return result

        except Exception as e:
            self.notify(f"Failed to call {capability}: {str(e)}", severity="error")
            return {"error": str(e)}

    def update_details_for_single_item(self, capability: str, item: Dict[str, Any]) -> None:
        """Update the details table to show information about a single capability item."""
        details_table = self.query_one("#details-table", DataTable)

        # Clear existing data
        details_table.clear()

        # Add columns
        details_table.add_columns("Field", "Value")

        # Add item details
        details_table.add_row("Type", capability.capitalize())
        details_table.add_row("Name", item.get("name", "unnamed"))
        details_table.add_row("Description", item.get("description", "No description"))
        
        # Add additional fields based on capability type
        if capability == "tool":
            input_schema = item.get("inputSchema", {})
            if input_schema:
                details_table.add_row("Input Schema", str(input_schema))
                # Add a row indicating this is executable
                details_table.add_row("Action", "Click on this item to execute the tool")
        elif capability == "resource":
            uri = item.get("uri", "N/A")
            details_table.add_row("URI", uri)
            details_table.add_row("Action", "Click on this item to read the resource")
        elif capability == "prompt":
            arguments = item.get("arguments", [])
            details_table.add_row("Arguments", str(arguments))
            details_table.add_row("Action", "Click on this item to execute the prompt")

    async def load_capability_items(self, capability: str, server_url: str, server_name: str) -> None:
        """Load items for a specific capability (tools, resources, or prompts)."""
        try:
            client = StreamableHTTPClient(server_url)
            await client.connect()

            # Initialize the connection
            init_response = await client.initialize()
            await client.initialized(init_response.get("result", {}))

            items_list = []
            if capability == "tools":
                response = await client.list_tools()
                items_list = response.get("result", {}).get("tools", [])
            elif capability == "resources":
                response = await client.list_resources()
                items_list = response.get("result", {}).get("resources", [])
            elif capability == "prompts":
                try:
                    response = await client.send_request("prompts/list")
                    items_list = response.get("result", {}).get("prompts", [])
                except:
                    items_list = []

            # Update the details table
            self.update_details_table(capability, items_list)

            await client.close()

        except Exception as e:
            self.notify(f"Failed to load {capability}: {str(e)}", severity="error")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle selection of a capability item row."""
        try:
            # Get the capability type from the table header or stored state
            # For now, we'll determine the action based on the first column
            if event.cursor_row >= 0:
                details_table = self.query_one("#details-table", DataTable)
                row_data = details_table.get_row_at(event.cursor_row)

                # Check if this is the single item view (2 columns: Field, Value) or the list view (3 columns: Type, Name, Description)
                if len(row_data) == 2:  # Single item view (Field, Value)
                    # This means we're viewing details of a single item
                    # If the selected row is for a tool, we can show the tool form
                    field_name = row_data[0]
                    field_value = row_data[1]

                    if field_name == "Type" and field_value.lower() == "tool":
                        # Find the tool in the current tools list and show form
                        if hasattr(self, 'current_tools') and self.current_tools:
                            # Find the tool name from the table
                            for i in range(details_table.row_count):
                                row = details_table.get_row_at(i)
                                if row[0] == "Name":
                                    tool_name = row[1]
                                    selected_tool = next((t for t in self.current_tools if t.get("name") == tool_name), None)
                                    if selected_tool:
                                        self.show_tool_form(selected_tool)
                                    break
                elif len(row_data) == 3:  # List view (Type, Name, Description)
                    capability_type = row_data[0]  # First column is capability type
                    item_name = row_data[1]       # Second column is name

                    if capability_type == "Tool" and hasattr(self, 'current_tools') and self.current_tools:
                        # Find the specific tool
                        selected_tool = next((t for t in self.current_tools if t.get("name") == item_name), None)
                        if selected_tool:
                            self.show_tool_form(selected_tool)
                    # TODO: Add handlers for resources and prompts when implemented
        except Exception as e:
            self.notify(f"Error processing row selection: {str(e)}", severity="error")
    
    def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key == "tab":
            # Switch focus between panels
            current_focus = self.focused
            if current_focus.id == "infrastructure-tree":
                self.query_one("#details-table").focus()
            else:
                self.query_one("#infrastructure-tree").focus()
        elif event.key == "f2":
            # Add custom registry
            self.push_screen(AddRegistryScreen(self.registry_manager))
        elif event.key == "f8":
            # Quit application
            self.exit()
        elif event.key == "ctrl+r":
            # Refresh current view
            if self.focused.id == "infrastructure-tree":
                self.call_later(self.load_infrastructure)
            elif self.focused.id == "details-table" and self.current_server_url:
                # Refresh the currently selected capability
                # For now, just reload infrastructure
                self.call_later(self.load_infrastructure)
    
    async def connect_to_server(self, server_url: str, server_name: str) -> None:
        """Connect to an MCP server and fetch all its capabilities (tools, resources, prompts)."""
        try:
            client = StreamableHTTPClient(server_url)
            await client.connect()

            # Initialize the connection
            init_response = await client.initialize()
            await client.initialized(init_response.get("result", {}))

            # Fetch all capabilities
            # List tools
            tools_response = await client.list_tools()
            tools_list = tools_response.get("result", {}).get("tools", [])

            # List resources
            resources_response = await client.list_resources()
            resources_list = resources_response.get("result", {}).get("resources", [])

            # List prompts (if the server supports it)
            try:
                # Note: There's no standard MCP method for listing prompts yet, 
                # but we'll try to call it in case the server supports it
                prompts_response = await client.send_request("prompts/list")
                prompts_list = prompts_response.get("result", {}).get("prompts", [])
            except:
                # If prompts/list is not supported, set an empty list
                prompts_list = []

            # Store current server info
            self.current_server = server_name
            self.current_server_url = server_url
            self.current_tools = tools_list
            self.current_resources = resources_list
            self.current_prompts = prompts_list

            # Update the tree view to show all capabilities
            await self.update_server_capabilities_tree(server_name, tools_list, resources_list, prompts_list)

            await client.close()

        except Exception as e:
            self.notify(f"Failed to connect to server: {str(e)}", severity="error")

    async def update_server_capabilities_tree(self, server_name: str, tools_list: List[Dict[str, Any]], 
                                           resources_list: List[Dict[str, Any]], 
                                           prompts_list: List[Dict[str, Any]]) -> None:
        """Update the tree view to show server capabilities hierarchy."""
        # Use call_after_refresh to ensure UI updates happen after render
        def update_ui():
            # Clear the right panel
            details_table = self.query_one("#details-table", DataTable)
            details_table.clear()
            details_table.add_columns("Capability Type", "Name", "Description")

            # Add rows for each capability type
            for tool in tools_list:
                details_table.add_row("Tool", tool.get("name", "unnamed"), tool.get("description", "No description"))
            
            for resource in resources_list:
                details_table.add_row("Resource", resource.get("name", "unnamed"), resource.get("description", "No description"))
            
            for prompt in prompts_list:
                details_table.add_row("Prompt", prompt.get("name", "unnamed"), prompt.get("description", "No description"))

        self.call_after_refresh(update_ui)
    
    def update_details_table(self, capability_type: str, items: List[Dict[str, Any]]) -> None:
        """Update the details table with capability items."""
        details_table = self.query_one("#details-table", DataTable)

        # Clear existing data
        details_table.clear()

        # Add columns
        details_table.add_columns("Type", "Name", "Description")

        # Add rows based on capability type
        for item in items:
            item_name = item.get('name', 'unnamed')
            description = item.get("description", "No description")
            details_table.add_row(capability_type.capitalize(), item_name, description)

    def update_tools_table(self, tools: List[Dict[str, Any]]) -> None:
        """Update the tools table with the given tools."""
        # This method is kept for backward compatibility but redirects to the new method
        self.update_details_table("tool", tools)
    
    async def refresh_tools(self) -> None:
        """Refresh the current tools list."""
        if self.current_server_url and self.current_server:
            # For now, just reconnect to reload all capabilities
            await self.connect_to_server(self.current_server_url, self.current_server)
    
    async def call_resource_directly(self, item: Dict[str, Any], server_url: str) -> None:
        """Directly call a resource capability."""
        try:
            result = await self.call_capability_on_server("resource", item, server_url)
            if "error" not in result:
                self.notify(f"Resource read result: {result.get('result', result)}", severity="information")
            else:
                self.notify(f"Resource read failed: {result['error']}", severity="error")
        except Exception as e:
            self.notify(f"Failed to read resource: {str(e)}", severity="error")

    def show_tool_form(self, tool: Dict[str, Any], server_url: str = None) -> None:
        """Show the tool form for the selected tool."""
        actual_server_url = server_url or self.current_server_url
        if actual_server_url:
            try:
                # Get server name from the URL or use a default
                # Extract server name from URL if current_server is not set
                if hasattr(self, 'current_server') and self.current_server:
                    server_name = self.current_server
                else:
                    # Extract server name from URL
                    parsed_url = urllib.parse.urlparse(actual_server_url)
                    server_name = f"{parsed_url.hostname}:{parsed_url.port}" if parsed_url.port else parsed_url.hostname

                tool_name = f"{server_name}__{tool.get('name', 'unnamed')}"
                
                # Sanitize the tool name to make it a valid ID (replace invalid characters)
                sanitized_tool_name = tool_name.replace(':', '_').replace('.', '_').replace('/', '_')

                # Also sanitize the form ID prefix to ensure it's valid for widget IDs
                sanitized_form_id_prefix = f"field-{tool_name.replace(' ', '_').replace(':', '_').replace('.', '_').replace('/', '_')}"

                # Validate that the tool has a proper input schema
                input_schema = tool.get("inputSchema", {})
                if not isinstance(input_schema, dict):
                    self.notify(f"Invalid input schema for tool {tool.get('name', 'unnamed')}", severity="error")
                    return

                # Create the tool form screen with the sanitized tool name
                tool_form_screen = ToolFormScreen(tool, sanitized_tool_name, actual_server_url)

                # Push the screen to the app
                self.push_screen(tool_form_screen)
                
            except Exception as e:
                self.notify(f"Error showing tool form: {str(e)}", severity="error")
        else:
            self.notify("No server URL available to execute tool", severity="error")