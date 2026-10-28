#!/bin/zsh
cd "${0:A:h}"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'NextRole 需要 Python 3.10 或以上版本。'
  exit 1
fi
python3 server.py
