from subprocess import check_output

docker_id_cmd = 'docker ps | grep homepage_production_postgres | cut -d " " -f 1'
postgres_id = (check_output(docker_id_cmd, shell=True)
               .decode('utf-8')
               .replace("\n", "")[:12])
print(postgres_id)

backup_cmd = 'docker-compose -f production.yml run postgres backup | cut -d " " -f 5'
backup_name = (check_output(backup_cmd, shell=True)
               .decode('utf-8')
               .replace("\n", ""))
# there are weird escape sequences in backup_name
backup_name = "".join([c for c in backup_name if c.isalnum() or c in set(['.', '_'])])
print(backup_name)

copy_cmd = 'docker cp {}:/backups/{} backups'.format(
    postgres_id, backup_name)
print(copy_cmd)
result = check_output(copy_cmd, shell=True)
print(result)

ssh_cmd = 'scp homepage:site/backups/{} backups'.format(backup_name)
print(ssh_cmd)
