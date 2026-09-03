#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/streamlit ]; then
  echo "First run: follow the installation steps in README.md"
  exit 1
fi
exec .venv/bin/streamlit run app.py

