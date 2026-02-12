# Enhanced Prompts Functionality

The MCP server now includes enhanced prompts functionality with the following operations:

## Available Methods

### `prompts/list`
Lists all available prompts with pagination support.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "prompts/list",
  "params": {
    "pagination": {
      "limit": 10,
      "cursor": "cursor_value"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "result": {
    "prompts": [
      {
        "name": "example_prompt",
        "description": "An example prompt template",
        "arguments": [
          {
            "name": "subject",
            "type": "string",
            "description": "Subject for the prompt"
          }
        ]
      }
    ],
    "pagination": {
      "hasMore": false,
      "nextCursor": null
    }
  }
}
```

### `prompts/get`
Retrieves and resolves a specific prompt with provided arguments.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "prompts/get",
  "params": {
    "name": "example_prompt",
    "arguments": {
      "subject": "AI development"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "result": {
    "contents": [
      {
        "type": "text",
        "text": "This is an example prompt about AI development."
      }
    ]
  }
}
```

### `prompts/submit`
Submits a new prompt or updates an existing one.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "prompts/submit",
  "params": {
    "name": "my_new_prompt",
    "content": "Generate code for {{task}} in {{language}}.",
    "description": "A flexible code generation prompt",
    "arguments": [
      {
        "name": "task",
        "type": "string",
        "description": "The task to generate code for"
      },
      {
        "name": "language",
        "type": "string",
        "description": "The programming language"
      }
    ],
    "tags": ["code-generation", "template"]
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "result": {
    "result": "success",
    "message": "Prompt 'my_new_prompt' submitted successfully",
    "prompt": {
      "name": "my_new_prompt",
      "description": "A flexible code generation prompt",
      "content": "Generate code for {{task}} in {{language}}.",
      "arguments": [...],
      "tags": ["code-generation", "template"],
      "created_at": 1234567890.123,
      "updated_at": 1234567890.123
    }
  }
}
```

### `prompts/update`
Updates an existing prompt.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "4",
  "method": "prompts/update",
  "params": {
    "name": "my_new_prompt",
    "content": "Generate optimized code for {{task}} in {{language}}.",
    "description": "An optimized code generation prompt"
  }
}
```

### `prompts/delete`
Deletes a prompt.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "5",
  "method": "prompts/delete",
  "params": {
    "name": "my_new_prompt"
  }
}
```

### `prompts/search`
Searches for prompts by name, content, or tags.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "6",
  "method": "prompts/search",
  "params": {
    "query": "code",
    "tags": ["generation"],
    "limit": 10
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "6",
  "result": {
    "prompts": [...],
    "total_matches": 1,
    "query": "code",
    "tags": ["generation"]
  }
}
```

### `prompts/export`
Exports prompts to JSON format.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": "7",
  "method": "prompts/export",
  "params": {
    "names": ["prompt1", "prompt2"]
  }
}
```

Or to export all prompts:
```json
{
  "jsonrpc": "2.0",
  "id": "8",
  "method": "prompts/export",
  "params": {
    "all": true
  }
}
```

## Storage

Prompts are stored as JSON files in the `prompts/` directory. Each prompt is saved as `{prompt_name}.json`.

## Argument Substitution

The system supports argument substitution in prompt content using double curly braces: `{{argument_name}}`.