import os
from subprocess import check_output

import paramiko

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# get backup dump from production
host = os.environ.get('PRODUCTION_HOST')
username = os.environ.get('PRODUCTION_USERNAME')
client = paramiko.SSHClient()
client.load_system_host_keys()
client.connect(host, username=username)

ssh_stdin, ssh_stdout, ssh_stderr = client.exec_command('cd site;python scripts/prod_backup.py')
stdout_lines = ssh_stdout.read().decode('utf-8').split('\n')
remote_path = None
for line in stdout_lines:
    if 'scp' in line:
        remote_path = line.split()[1].split(':')[-1]
print(remote_path)
file_name = os.path.basename(remote_path)
local_path = os.path.join('backups', file_name)

if not os.path.exists('backups'):
    os.mkdir('backups')
sftp = client.open_sftp()
sftp.get(remote_path, 'backups/{}'.format(file_name))

# recreate local docker environment from production

# restore backup dump to database
docker_id_cmd = 'docker ps | grep homepage_production_postgres | cut -d " " -f 1'
postgres_id = (check_output(docker_id_cmd, shell=True)
               .decode('utf-8')
               .replace("\n", ""))
print(postgres_id)

backup_copy_cmd = 'docker cp {} {}:/backups'.format(local_path, postgres_id)
print(backup_copy_cmd)
result = check_output(backup_copy_cmd, shell=True)
print(result)

docker_down = 'docker-compose -f local.yml down'
result = check_output(docker_down, shell=True)
print(result)

start_postgres_cmd = 'docker-compose -f local.yml run django ./manage.py'
result = check_output(start_postgres_cmd, shell=True)
print(result)

restore_cmd = 'docker-compose -f local.yml run postgres restore {}'.format(file_name)
print(restore_cmd)
result = check_output(restore_cmd, shell=True)
print(result)

# remove stale media files
#delete_stale_cmd = 'docker-compose -f local.yml run django ./manage.py s3_stale --delete'
#delete_stale_cmd = 'docker-compose -f local.yml run django ./manage.py s3_stale'
#print(delete_stale_cmd)
#result = check_output(delete_stale_cmd, shell=True)
#print(result)

# get new media files from s3
backup_s3_cmd = 'docker-compose -f local.yml run django ./manage.py s3_backup'
print(backup_s3_cmd)
result = check_output(backup_s3_cmd, shell=True)
print(result)

# recreate local db from production
dropdb_cmd = 'dropdb homepage'
print(dropdb_cmd)
result = check_output(dropdb_cmd, shell=True)
print(result)

createdb_cmd = 'createdb homepage'
print(createdb_cmd)
result = check_output(createdb_cmd, shell=True)
print(result)

local_restore_cmd = 'gunzip -c {} | psql homepage -U homepage'.format(local_path)
print(local_restore_cmd)
result = check_output(local_restore_cmd, shell=True)
print(result)
