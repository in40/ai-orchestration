#!/usr/bin/env python3
"""
Mock LLM Server for testing
"""
from flask import Flask, request, jsonify
import time
import json

app = Flask(__name__)

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.get_json()
    messages = data.get('messages', [])
    model = data.get('model', 'mock-model')
    
    # Simple mock response based on the input
    user_message = ""
    for msg in messages:
        if msg.get('role') == 'user':
            user_message = msg.get('content', '')
            break
    
    # Generate a mock response based on the user's request
    if "hello world" in user_message.lower():
        response_content = '''```python
# Simple Hello World App in Python
print("Hello, World!")

# Additional example with a function
def hello_world():
    """Prints a hello world message."""
    print("Hello, World from a function!")

if __name__ == "__main__":
    hello_world()
```

This is a simple Python program that prints "Hello, World!" to the console. The program includes:
1. A direct print statement
2. A function that prints the message
3. Proper `if __name__ == "__main__"` guard for good practice'''
    elif "health check" in user_message.lower():
        response_content = "OK"
    else:
        response_content = f"I've received your request: '{user_message[:50]}...' and processed it successfully."

    response = {
        "id": "cmpl-mock-" + str(int(time.time())),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(user_message.split()),
            "completion_tokens": len(response_content.split()),
            "total_tokens": len(user_message.split()) + len(response_content.split())
        }
    }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1234, debug=False)