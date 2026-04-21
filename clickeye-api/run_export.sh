#!/bin/bash
cd /mnt/c/workspace/24SevenClaw/24SevenClaw-api
PYTHONPATH=/mnt/c/workspace/24SevenClaw/24SevenClaw-api .venv/bin/python -c "
from scripts.export_openapi import export_openapi
export_openapi()
"
