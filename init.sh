#!/bin/bash -e

export AWS_DEFAULT_REGION="us-east-2"

# Open python virtual environment in directory ".venv".  See https://docs.python.org/3/library/venv.html
python3 -m venv .venv
# activate the virtual environment by sourcing the associated bin/activate file. See https://docs.python.org/3/tutorial/venv.html
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python simple-infrastructure.py
