@echo off
start cmd /k python -m server.main
timeout /t 2
start cmd /k python -m client.main