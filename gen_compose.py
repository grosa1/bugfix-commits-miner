import os
import sys
from math import floor
from datetime import datetime

mysql_user = '<PLACEHOLDER>'
mysql_pass = '<PLACEHOLDER>'
mysql_expose_port = '3307'
mysql_root_password = '<PLACEHOLDER>'
date_from = datetime(2015, 1, 1)

def extract_date(filename):
    return datetime.strptime(filename.split('.')[0], '%Y-%m-%d-%H')


## check for old docker-compose files
compose_file = 'docker-compose.yml'
if os.path.isfile(compose_file):
    os.remove(compose_file)

## read cli params
data_dir = sys.argv[1]
n_workers = floor(int(sys.argv[2]))

print('using data_dir', data_dir)
print('number of workers:', n_workers)

## read files
print(f'reading files from {data_dir} ...')
files = [f for f in os.listdir(data_dir) if f.endswith('.json.gz')]
files = sorted(files, key=lambda f: extract_date(f))
step = floor(len(files) / n_workers)
carry = len(files) - (step * n_workers)

print('files count:', len(files))
print('files per worker:', step)
print('carry for last worker:', carry)


## docker compose file template
compose_header = """
version : "2.1"

services:
"""

compose_worker = """
  szz_commits_worker_{worker_id}:
    image: szz_commits_worker
    container_name: szz_commits_worker_{worker_id}
    command: {from_file} {to_file}
    environment:
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_PASS={mysql_pass}
      - DB_USER={mysql_user} 
    volumes:
      - {data_dir}:/usr/src/app/data
    depends_on:
        mysql:
          condition: service_healthy
    restart: on-failure
"""

compose_tail = f"""
  mysql:
    image: mysql:5.7
    container_name: szz_commits_db
    environment:
      MYSQL_USER: {mysql_user}
      MYSQL_PASSWORD: {mysql_pass}
      MYSQL_ROOT_PASSWORD: {mysql_root_password}
      MYSQL_DATABASE: bugfix_commits
    volumes:
      - ./dump:/docker-entrypoint-initdb.d
      - szz_commits_data01:/var/lib/mysql
    ports:
      - {mysql_expose_port}:3306
    healthcheck:
        test: ["CMD", "mysqladmin" ,"ping", "-h", "localhost"]
        timeout: 20s
        retries: 10
    restart: always

volumes:
  szz_commits_data01:
    driver: local
"""
## END docker compose file template 


print('generating workers conf ...')
with open(compose_file, 'w') as out:
    out.write(compose_header)
    for i in range(n_workers):
        if i == (n_workers - 1):
            step += carry
        from_index = i * step
        from_file = files[from_index]
        to_index = (from_index + step) - 1
        if to_index < len(files): 
          to_file = files[to_index]
        else:
          to_file = files[-1]

        worker = compose_worker.format(worker_id=i + 1, 
                                        from_file=from_file, 
                                        to_file=to_file, 
                                        mysql_pass=mysql_pass, 
                                        mysql_user=mysql_user, 
                                        data_dir=data_dir)
        out.write(worker)
    
    out.write(compose_tail)

print('+++ DONE +++')
