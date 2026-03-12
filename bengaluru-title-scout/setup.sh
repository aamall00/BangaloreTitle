#!/bin/bash
echo "================================================"
echo "  Bengaluru Title Scout - First Time Setup"
echo "================================================"
echo ""
echo "[1] Installing Node.js dependencies..."
npm install
echo ""
echo "[2] Setting up Python backend..."
python3 backend/setup.py
echo ""
echo "================================================"
echo "  Setup complete! To start the app run:"
echo "  npm start"
echo "================================================"
