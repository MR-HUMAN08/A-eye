#!/bin/bash

echo "Starting FinPath MCP Server..."

echo "Backend check..."
curl -s http://localhost:8000/ | python3 -c "import sys,json; d=json.load(sys.stdin); print('Backend: OK -', d.get('status','unknown'))" || echo "WARNING: Backend not responding. Start it first with: cd /home/harini/cbit/finpath/backend && uvicorn main:app --port 8000"

echo "Ollama check..."
curl -s http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b","prompt":"ping","stream":false}' | python3 -c "import sys,json; json.load(sys.stdin); print('Ollama: OK')" || echo "WARNING: Ollama not responding."

echo "Starting MCP server on stdio + SSE :8001..."
source /home/harini/cbit/venv/bin/activate
python3 /home/harini/cbit/finpath/mcp_server/finpath_mcp_server.py
