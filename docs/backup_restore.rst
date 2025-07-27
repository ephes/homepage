Backup
======

How to backup the production database:
 * Use pg_dump or your preferred PostgreSQL backup tool
 * Store backups in a secure location

How to backup the s3 contents (copy to local media directory):
 * uv run python manage.py s3_backup

How to restore the local contents to s3 (copy local media directory to s3):
 * uv run python manage.py s3_restore

Restore
=======

How to restore the production backup to the local database:
 * scp homepage:site/backups/backup_2017_09_12T11_39_22.sql.gz backups
 * Use pg_restore or psql to restore the backup to your local PostgreSQL database
