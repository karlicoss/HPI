#!/bin/bash
python3.6 -mpylint -E main.py common.py products.py
python3.6 -mmypy main.py common.py products.py
