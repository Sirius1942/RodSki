#!/bin/bash
set -e

case "$1" in
  run)
    shift
    exec python3 cli_main.py run "$@" --headless
    ;;
  pytest)
    shift
    exec python3 -m pytest "$@"
    ;;
  report)
    shift
    exec python3 cli_main.py report "$@"
    ;;
  shell)
    exec /bin/bash
    ;;
  idle)
    echo "[rodski-sandbox] 沙箱就绪，等待命令..."
    exec tail -f /dev/null
    ;;
  *)
    exec "$@"
    ;;
esac
