#!/bin/bash -e

if [ -z "$1" ]
  then
    echo "Please provide github api access token .
        ./init.sh <<github apip access token>> "
    exit 1
fi

export AWS_DEFAULT_REGION="us-east-1"

# Open python virtual environment in directory ".venv".  See https://docs.python.org/3/library/venv.html
python3 -m venv .venv
# activate the virtual environment by sourcing the associated bin/activate file. See https://docs.python.org/3/tutorial/venv.html
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

python simple-infrastructure.py $1
