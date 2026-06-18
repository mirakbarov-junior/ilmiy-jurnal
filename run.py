#!/usr/bin/env python3
"""Run this once locally to test, or let gunicorn import app.py directly."""
from app import app, init_db

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
