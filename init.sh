#!/bin/bash -e

if [ -z "$1" ]
  then
    echo "Please provide github api access token .
        ./init.sh <<github apip access token>> "
    exit 1
fi

export AWS_DEFAULT_REGION="us-east-2"

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python simple-infrastructure.py $1
