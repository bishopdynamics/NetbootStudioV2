#!/usr/bin/env bash
# Monitor Netboot Studio logs

echo ""
echo " Will now monitor logs, ctrl+c to quit (NetbootStudio will continue running)"
echo ""
docker-compose logs -f
