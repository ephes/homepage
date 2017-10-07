Backup
======

How to backup the production database:
 * docker-compose -f production.yml run postgres backup
 * docker cp f7a499e33d19:/backups/backup_2017_09_12T11_39_22.sql.gz backups

How to backup the s3 contents (copy to local media directory):
 * docker-compose -f local.yml run django ./manage.py s3_backup

How to restore the local contents to s3 (copy local media directory to s3):
 * docker-compose -f local.yml run django ./manage.py s3_restore

Restore
=======

How to restore the production backup to the local database:
 * scp homepage:site/backups/backup_2017_09_12T11_39_22.sql.gz backups
 * Make sure POSTGRES_PASSWORD is present in postgres local.yml environment
 * docker cp backups/backup_2017_09_12T11_39_22.sql.gz 68c8d4952563:/backups
 * docker-compose -f local.yml run postgres restore backup_2017_09_12T11_39_22.sql.gz
