@echo off
title Xiaomi Router Manager
cd /d "%~dp0"
uv run --with customtkinter --with cryptography python gui.py
