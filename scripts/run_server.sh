#!/bin/bash

cd /home/ubuntu/vdezi_ai_sales_prediction    #relace service_repowith  your repo name 

git stash

git pull origin master

source ./venv/bin/activate

pip3 install -r requirements.txt 

python3 serve.py



