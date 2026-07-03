#!/usr/bin/env python3
"""Orion Video Player - Launch script."""

import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orion.app import main

if __name__ == '__main__':
    sys.exit(main())
