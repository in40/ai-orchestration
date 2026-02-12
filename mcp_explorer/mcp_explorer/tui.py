"""TUI for MCP Explorer using textual library."""
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header, Footer, Tree, DataTable, Static, 
    Button, Input, Label, Checkbox, Select
)
from textual.screen import ModalScreen, Screen
from textual import on
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
            with Container(id="results-container-wrapper"):
                with ScrollableContainer(id="results-container"):
                    # Use a Static widget for results display, with scrolling container
                    self.results_display = Static("", id="results-display", markup=False)
                    self.results_display.can_focus = True
                    self.results_display.expand = True
                    self.results_display.shrink = True
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
                self.results_display.update("")
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
            # Use the app's centralized method to call the capability
            result = await self.app.call_capability_on_server("tool", self.tool_schema, self.server_url, arguments)

            # Display result in the form instead of notification
            if "error" not in result:
                # Pass the actual result object to preserve structure
                self.display_result(result, is_error=False)
            else:
                error_text = f"Tool execution failed:\n{result['error']}"
                self.display_result(error_text, is_error=True)
        except Exception as e:
            error_text = f"Error calling tool:\n{str(e)}"
            self.display_result(error_text, is_error=True)

        # Keep the form open for additional submissions
        # self.app.pop_screen() - removed this line

    def display_result(self, result_data, is_error: bool = False):
        """Display the result in the results area."""
        if self.results_display:
            try:
                import json
                
                # Handle different types of result data
                if isinstance(result_data, dict):
                    # If it's an error response
                    if is_error:
                        plain_text = json.dumps(result_data, indent=2)
                        self.results_display.update(plain_text)
                        return
                    
                    # Check if it's a structured response with a 'result' field
                    if 'result' in result_data:
                        actual_result = result_data['result']
                        
                        if isinstance(actual_result, list):
                            # If it's a list (like tasks), render as a table
                            self.render_list_as_table(actual_result)
                        elif isinstance(actual_result, dict):
                            # If it's a dict, render as a table with key-value pairs
                            self.render_dict_as_table(actual_result)
                        else:
                            # For other types, display as formatted text
                            plain_text = json.dumps(actual_result, indent=2)
                            self.results_display.update(plain_text)
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
                                        plain_text = json.dumps(actual_result, indent=2)
                                        self.results_display.update(plain_text)
                                else:
                                    self.render_dict_as_table(parsed_result)
                            else:
                                # For other types, display as formatted text
                                plain_text = json.dumps(parsed_result, indent=2)
                                self.results_display.update(plain_text)
                        except json.JSONDecodeError:
                            # If it's not JSON, display as plain text
                            self.results_display.update(result_data)
                    else:
                        # If it's a plain string, display as formatted text
                        self.results_display.update(result_data)
                else:
                    # For other types, display as formatted text
                    plain_text = json.dumps(result_data, indent=2)
                    self.results_display.update(plain_text)
                    
            except Exception as e:
                # If anything goes wrong, fall back to the original behavior
                import json
                plain_text = json.dumps(result_data, indent=2)
                self.results_display.update(plain_text)

    def render_list_as_table(self, data_list):
        """Render a list of items as a user-friendly table."""
        import json
        
        if not data_list:
            # Update the existing display with a message
            self.results_display.update("No items found in the list.")
            return
            
        # Check if this looks like a job/task list (has common fields like taskId, status, etc.)
        # First, make sure data_list[0] exists and is a dict before accessing it
        if data_list and isinstance(data_list[0], dict):
            # Check for common job/task fields
            first_item = data_list[0]
            if any(field in first_item for field in ['taskId', 'jobId', 'id', 'task_id', 'job_id']):
                try:
                    # This looks like a job/task list, create a user-friendly display
                    result_text = self.format_job_list(data_list)
                    self.results_display.update(result_text)
                    return
                except Exception as e:
                    # If there's an error in formatting, fall back to JSON
                    pass
        
        # For other types of lists, just display as formatted JSON
        self.results_display.update(json.dumps(data_list, indent=2))
    
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
            self.results_display.update("Dictionary is empty.")
            return
            
        # Just display as formatted JSON since we're using Static widget
        # but at least the text will be viewable
        self.results_display.update(json.dumps(data_dict, indent=2))

    def copy_cell_to_clipboard(self, event):
        """Copy the content of the selected cell to clipboard."""
        try:
            # Get the selected row and column
            row_key = event.row_key.value
            column_key = event.column_key.value
            
            # Get the value from the table
            table = event.sender
            value = table.get_cell_at(row_key, column_key)
            
            # For now, just show a notification since we can't directly access system clipboard in this context
            self.app.notify(f"Copied to clipboard: {value}", severity="information")
            
        except Exception as e:
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
            client = StreamableHTTPClient(server_url)
            await client.connect()

            # Initialize the connection if not already done
            if not hasattr(self, '_initialized_servers'):
                self._initialized_servers = set()
            
            if server_url not in self._initialized_servers:
                init_response = await client.initialize()
                await client.initialized(init_response.get("result", {}))
                self._initialized_servers.add(server_url)

            result = None
            if capability == "tool":
                # Call the tool with arguments - extract the actual tool name from the canonical name
                # The item passed in might be the tool schema, so get the name from it
                tool_name = item.get("name", "")
                # If the tool_name is empty, try to extract from the item itself
                if not tool_name and hasattr(item, 'get'):
                    # If item is the schema dictionary, get name from it
                    tool_name = item.get("name", "")
                
                result = await client.call_tool(tool_name, arguments or {})
            elif capability == "resource":
                # Read the resource
                resource_uri = item.get("uri", "")
                result = await client.read_resource(resource_uri)
            elif capability == "prompt":
                # For prompts, we might need a different approach depending on server implementation
                # This is a placeholder for now
                result = {"error": "Prompt execution not yet implemented"}

            await client.close()
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