
# This Dockerfile sets up a Python3.7 and WKHtmlToPDF environment as well as an nginx environment with static files

FROM python:3.7-buster as app

ADD config/fontconfig.xml /etc/fonts/local.conf

WORKDIR /usr/src

RUN apt-get update && \
    apt-get install -y python3-pip python3-dev gettext libssl-dev xfonts-scalable fonts-lmodern \
    fonts-stix fonts-liberation locales wkhtmltopdf \
    libbluetooth-dev tk-dev uuid-dev \
    && rm -rf /var/lib/apt/lists/* \
    && echo en_US.UTF-8 UTF-8 > /etc/locale.gen \
    && echo fr_CA.UTF-8 UTF-8 >> /etc/locale.gen \
    && /usr/sbin/locale-gen

ENV LANG C.UTF-8

EXPOSE 80

STOPSIGNAL SIGTERM

# CMD ["nginx", "-g", "daemon off;"]

CMD ["python3"]

WORKDIR /app
ADD requirements.txt /app/requirements.txt


RUN pip3 install --upgrade pip setuptools && \
    pip3 install -r requirements.txt && \
    rm -rf /root/.cache && \
    mkdir -p /app/media/uploads && \
    groupadd -g 1000 sis && \
    useradd --shell /bin/bash -u 1000 -g 1000 -c "" -d /app -m sis

ADD . /app

# Setup media directory
VOLUME ["/app/media/uploads"]

# Setup Environment
ENV PYTHON_PATH=/app

# Generate static assets
RUN cd /app && \
    export SECRET_KEY=test; \
    ./manage.py collectstatic --noinput; \
    ./manage.py compress --force

ADD run-production.sh /
CMD /run-production.sh uwsgi --http 0.0.0.0:8080 --chdir=/app \
    --module=sis.wsgi:application --processes=2 \
    --uid 1000 --threads=4 --harakiri=300 \
    --max-requests=5000 --vacuum --die-on-term

EXPOSE 8080

FROM nginx:1.19 as static

COPY --from=app /app/static /app/static

ADD config/nginx.conf /etc/nginx/nginx.conf
