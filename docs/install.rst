Install
=========

This is where you write how to get a new laptop to run this project.

Production
==========

To deploy this project on a production machine, follow those steps:
 * apt install python3-pip supervisor postgresql
 * pip3 install uv
 * Create PostgreSQL database and user for the application
 * Configure environment variables for database access
 * ln -s /home/homepage/homepage/supervisor.conf /etc/supervisor/conf.d/homepage.conf
 * supervisorctl reload
 * supervisorctl start homepage
