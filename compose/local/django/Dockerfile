FROM python:3.5

ENV PYTHONUNBUFFERED 1

# being able to use apt
RUN apt update
RUN apt -y upgrade

# requirements for ffmpeg (need it to get thumbnails for videos)
RUN apt install -y software-properties-common
RUN apt-add-repository -y ppa:ubuntugis/ppa

# Requirements have to be pulled and installed here, otherwise caching won't work
COPY ./requirements /requirements
RUN pip install -r /requirements/local.txt

COPY ./compose/production/django/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r//' /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY ./compose/local/django/start.sh /start.sh
RUN sed -i 's/\r//' /start.sh
RUN chmod +x /start.sh

COPY ./compose/local/django/celery/worker/start.sh /start-celeryworker.sh
RUN sed -i 's/\r//' /start-celeryworker.sh
RUN chmod +x /start-celeryworker.sh

COPY ./compose/local/django/celery/beat/start.sh /start-celerybeat.sh
RUN sed -i 's/\r//' /start-celerybeat.sh
RUN chmod +x /start-celerybeat.sh

WORKDIR /app

ENV DJANGO_READ_DOT_ENV_FILE=True

ENTRYPOINT ["/entrypoint.sh"]
