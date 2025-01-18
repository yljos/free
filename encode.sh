#!/bin/bash
cat 0 | python -c "import sys, urllib.parse; print(urllib.parse.quote(sys.stdin.read().strip()))" > web.txt

