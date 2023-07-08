#!/bin/bash

data_dir=$1
n_workers=$2

echo '1. building worker container image'
docker build --no-cache -t szz_commits_worker src/. || exit 1

echo '2. generating docker-compose file'
python3 gen_compose.py ${data_dir} ${n_workers} || exit 1

echo '3. starting docker-compose'
docker-compose up -d