Install
=========

This is where you write how to get a new laptop to run this project.

Production
==========

To deploy this project on a production machine, follow those steps:
 * apt install docker.io python3-pip supervisor
 * pip3 install docker-compose
 * sudo usermod -aG docker homepage
 * systemctl start docker
 * ln -s /home/homepage/homepage/supervisor.conf /etc/supervisor/conf.d/homepage.conf
 * supervisorctl reload
 * supervisorctl start homepage
