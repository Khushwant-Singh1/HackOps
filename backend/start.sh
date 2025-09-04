#!/bin/bash

# Start HackOps FastAPI Application
cd /home/anuragisinsane/HackOps/backend
export PYTHONPATH=$(pwd)
python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0
