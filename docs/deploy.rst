Deploy
========

When code is changed, do this to deploy it in prodution:
 * supervisectl stop homepage
 * docker-compose -f production.yml down
 * docker-compose -f production.yml build
 * docker-compose -f production.yml up
