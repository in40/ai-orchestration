"""Read-only TUI for MCP Explorer using textual library."""
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Tree, DataTable, Static,
    Button, Input, Label, Checkbox, Select
)
from textual.screen import ModalScreen, Screen
from textual import on
from textual.message import Message
from .registry_adapters_readonly import ReadOnlyRegistryManager, ReadOnlyLocalhostRegistryAdapter
from typing import Dict, Any, List, Optional
import asyncio
import urllib.parse


class ConnectionErrorScreen(Screen):
    """Screen shown when registry connection fails."""

    def __init__(self, registry_manager):
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
                yield Static("F2 Add Custom Registry (DISABLED)", id="add-registry-disabled", variant="warning")
                yield Button("F8 Quit", id="quit-btn", variant="error")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit-btn":
            self.app.exit()


class ReadOnlyToolFormScreen(ModalScreen):
    """Read-only modal screen for tool parameter display."""

    def __init__(self, tool_schema: Dict[str, Any], tool_name: str):
        super().__init__()
        self.tool_schema = tool_schema
        self.tool_name = tool_name
        # Ensure input_schema is a dict to prevent errors in form generation
        self.input_schema = tool_schema.get("inputSchema", {}) or {}

    def compose(self) -> ComposeResult:
        with Container(id="tool-form-modal"):
            yield Static(f"Tool: {self.tool_name}", id="tool-title")
            
            # Display tool information in read-only format
            yield Static("Tool Information:", id="tool-info-header")
            
            # Add tool details
            if "description" in self.tool_schema:
                yield Static(f"Description: {self.tool_schema['description']}", id="tool-description")
            
            if "inputSchema" in self.tool_schema:
                yield Static("Input Schema:", id="input-schema-header")
                
                input_schema = self.tool_schema["inputSchema"]
                if "properties" in input_schema:
                    properties = input_schema["properties"]
                    for prop_name, prop_details in properties.items():
                        field_type = prop_details.get("type", "string")
                        description = prop_details.get("description", "No description")
                        required = " (required)" if prop_name in input_schema.get("required", []) else ""
                        
                        yield Static(f"- {prop_name} ({field_type}){required}: {description}", id=f"prop-{prop_name}")
                
                if "required" in input_schema:
                    required_fields = ", ".join(input_schema["required"])
                    yield Static(f"Required fields: {required_fields}", id="required-fields")
            
            with Container(id="results-container-wrapper"):
                with ScrollableContainer(id="results-container"):
                    # Use a DataTable widget for better results display (even though it's read-only)
                    self.results_display = DataTable(id="results-display")
                    self.results_display.can_focus = True
                    self.results_display.expand = True
                    self.results_display.shrink = True
                    # Add a simple message to the table
                    self.results_display.add_columns("Information")
                    self.results_display.add_row("This is a read-only view. Tool execution is disabled.")
                    
                    yield self.results_display

            with Horizontal(id="form-buttons"):
                yield Static("F7 Call Tool (DISABLED)", id="call-tool-disabled", variant="warning")
                yield Button("Close", id="close-btn", variant="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-btn":
            # Close the modal
            self.app.pop_screen()

    async def on_key(self, event) -> None:
        """Handle key presses."""
        if event.key == "escape":
            # Close the modal when Escape is pressed
            self.app.pop_screen()


class MCPExplorerReadOnlyApp(App):
    """Read-only MCP Explorer TUI Application."""

    TITLE = "MCP Explorer (Read-Only)"
    SUB_TITLE = "Model Context Protocol Explorer (Streamable HTTP) - READ ONLY MODE"
    CSS_PATH = "mcp_explorer.tcss"

    def __init__(self, expand_all_by_default=True):
        super().__init__()
        self.registry_manager = ReadOnlyRegistryManager()
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
                Tree("Registry (Read-Only)", id="infrastructure-tree"),
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
        self.call_later(self.load_infrastructure_readonly)

    async def load_infrastructure_readonly(self) -> None:
        """Load registries and populate the infrastructure tree in read-only mode."""
        try:
            # For read-only mode, we'll simulate some sample data
            # In a real implementation, you might load from cached data or static files
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
                    await self.pre_populate_and_expand_capabilities_readonly(server_node, server["url"])

        except Exception as e:
            self.call_after_refresh(lambda: self.notify(f"Error loading infrastructure: {str(e)}", severity="error"))

    async def pre_populate_and_expand_capabilities_readonly(self, server_node, server_url: str):
        """Pre-populate and expand capability nodes to show all items in read-only mode."""
        for capability_node in server_node.children:
            if capability_node.data and capability_node.data.get("type") == "capability":
                capability = capability_node.data["capability"]

                # Populate the capability node with its items
                await self.populate_capability_children_readonly(capability_node, capability, server_url)

                # Expand the capability node to show all items
                capability_node.expand()

    async def populate_capability_children_readonly(self, capability_node, capability: str, server_url: str) -> None:
        """Populate children nodes for a capability node with individual items in read-only mode."""
        try:
            # In read-only mode, we'll simulate loading data or use cached data
            # For demonstration purposes, we'll create some sample data
            items_list = []
            
            # Simulate loading data based on capability type
            if capability == "tools":
                items_list = [
                    {"name": "sample-tool-1", "description": "A sample tool for demonstration"},
                    {"name": "sample-tool-2", "description": "Another sample tool"},
                ]
            elif capability == "resources":
                items_list = [
                    {"name": "sample-resource-1", "description": "A sample resource"},
                    {"name": "sample-resource-2", "description": "Another sample resource"},
                ]
            elif capability == "prompts":
                items_list = [
                    {"name": "sample-prompt-1", "description": "A sample prompt"},
                    {"name": "sample-prompt-2", "description": "Another sample prompt"},
                ]

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

        except Exception as e:
            self.notify(f"Failed to load {capability} children: {str(e)}", severity="error")

    async def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle selection of a node in the infrastructure tree."""
        selected_node = event.node
        if selected_node.data:
            node_data = selected_node.data
            node_type = node_data.get("type")

            if node_type == "server":
                # Show server information in read-only mode
                server_info = node_data["info"]
                await self.show_server_info_readonly(server_info["url"], server_info["name"])
            elif node_type == "capability":
                # Load specific capability items (tools, resources, or prompts) and add them as children
                capability = node_data["capability"]
                server_info = node_data["server_info"]

                # If the node has no children yet, fetch and add them
                if not selected_node.children:
                    await self.populate_capability_children_readonly(selected_node, capability, server_info["url"])

                # Expand the node to show children
                selected_node.expand()

                # Update the details panel to show the items
                await self.load_capability_items_readonly(capability, server_info["url"], server_info["name"])
            elif node_type == "capability_item":
                # Handle selection of individual capability items
                item = node_data["item"]
                capability = node_data["capability"]
                server_url = node_data["server_url"]

                # Update the details panel to show information about this specific item
                self.update_details_for_single_item_readonly(capability, item)

                # For tools, show read-only form
                if capability == "tools":
                    # Show read-only tool form
                    self.show_readonly_tool_form(item)

    def update_details_for_single_item_readonly(self, capability: str, item: Dict[str, Any]) -> None:
        """Update the details table to show information about a single capability item in read-only mode."""
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
                # Add a row indicating this is read-only
                details_table.add_row("Action", "Read-only view - execution disabled")
        elif capability == "resource":
            uri = item.get("uri", "N/A")
            details_table.add_row("URI", uri)
            details_table.add_row("Action", "Read-only view - resource reading disabled")
        elif capability == "prompt":
            arguments = item.get("arguments", [])
            details_table.add_row("Arguments", str(arguments))
            details_table.add_row("Action", "Read-only view - prompt execution disabled")

    async def load_capability_items_readonly(self, capability: str, server_url: str, server_name: str) -> None:
        """Load items for a specific capability (tools, resources, or prompts) in read-only mode."""
        try:
            # In read-only mode, we'll simulate loading data or use cached data
            # For demonstration purposes, we'll create some sample data
            items_list = []
            
            if capability == "tools":
                items_list = [
                    {"name": "sample-tool-1", "description": "A sample tool for demonstration"},
                    {"name": "sample-tool-2", "description": "Another sample tool"},
                ]
            elif capability == "resources":
                items_list = [
                    {"name": "sample-resource-1", "description": "A sample resource"},
                    {"name": "sample-resource-2", "description": "Another sample resource"},
                ]
            elif capability == "prompts":
                items_list = [
                    {"name": "sample-prompt-1", "description": "A sample prompt"},
                    {"name": "sample-prompt-2", "description": "Another sample prompt"},
                ]

            # Update the details table
            self.update_details_table_readonly(capability, items_list)

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
                    # If the selected row is for a tool, we can show the read-only tool form
                    field_name = row_data[0]
                    field_value = row_data[1]

                    if field_name == "Type" and field_value.lower() == "tool":
                        # Find the tool in the current tools list and show read-only form
                        if hasattr(self, 'current_tools') and self.current_tools:
                            # Find the tool name from the table
                            for i in range(details_table.row_count):
                                row = details_table.get_row_at(i)
                                if row[0] == "Name":
                                    tool_name = row[1]
                                    selected_tool = next((t for t in self.current_tools if t.get("name") == tool_name), None)
                                    if selected_tool:
                                        self.show_readonly_tool_form(selected_tool)
                                    break
                elif len(row_data) == 3:  # List view (Type, Name, Description)
                    capability_type = row_data[0]  # First column is capability type
                    item_name = row_data[1]       # Second column is name

                    if capability_type == "Tool" and hasattr(self, 'current_tools') and self.current_tools:
                        # Find the specific tool
                        selected_tool = next((t for t in self.current_tools if t.get("name") == item_name), None)
                        if selected_tool:
                            self.show_readonly_tool_form(selected_tool)
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
            # Add custom registry - disabled in read-only mode
            self.notify("Add custom registry is disabled in read-only mode", severity="warning")
        elif event.key == "f8":
            # Quit application
            self.exit()
        elif event.key == "ctrl+r":
            # Refresh current view - disabled in read-only mode
            self.notify("Refresh is disabled in read-only mode", severity="warning")
        elif event.key == "f7":
            # Call tool - disabled in read-only mode
            self.notify("Tool execution is disabled in read-only mode", severity="warning")

    async def show_server_info_readonly(self, server_url: str, server_name: str) -> None:
        """Show server information in read-only mode."""
        try:
            # In read-only mode, we'll just display server info without connecting
            details_table = self.query_one("#details-table", DataTable)
            details_table.clear()
            details_table.add_columns("Property", "Value")
            
            details_table.add_row("Server Name", server_name)
            details_table.add_row("URL", server_url)
            details_table.add_row("Status", "Read-only view")
            details_table.add_row("Connection", "Not established (read-only)")

        except Exception as e:
            self.notify(f"Failed to show server info: {str(e)}", severity="error")

    def update_details_table_readonly(self, capability_type: str, items: List[Dict[str, Any]]) -> None:
        """Update the details table with capability items in read-only mode."""
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

    def show_readonly_tool_form(self, tool: Dict[str, Any]) -> None:
        """Show the read-only tool form for the selected tool."""
        try:
            # Sanitize the tool name to make it a valid ID (replace invalid characters)
            tool_name = tool.get('name', 'unnamed')
            sanitized_tool_name = tool_name.replace(':', '_').replace('.', '_').replace('/', '_')

            # Create the read-only tool form screen
            tool_form_screen = ReadOnlyToolFormScreen(tool, sanitized_tool_name)

            # Push the screen to the app
            self.push_screen(tool_form_screen)

        except Exception as e:
            self.notify(f"Error showing read-only tool form: {str(e)}", severity="error")