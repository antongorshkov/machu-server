# Machu Server Documentation

This directory contains documentation for the Machu Server API.

## Available Documentation

- [API Documentation](api_documentation.md) - Detailed information about the backend APIs, including request/response formats for directory entry management (adding, updating, and deleting contacts)

## Running the Server

To run the Machu Server locally:

```bash
cd /Users/antongorshkov/Documents/GitHub/machu-server && source .venv/bin/activate && flask run --host=192.168.68.58 --port=5000
```

This command:
1. Changes to the project directory
2. Activates the Python virtual environment
3. Starts the Flask server on the specific IP and port

## How to Use

Review the documentation files to understand the expected payloads and responses for each API endpoint. This information is particularly useful when developing or debugging the frontend components that interact with these APIs.

## Development Notes

When implementing new APIs or modifying existing ones, please update the documentation accordingly to keep it in sync with the actual implementation.
