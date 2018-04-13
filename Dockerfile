# Using the Ubuntu image
FROM debian:jessie

MAINTAINER Project Jupyter <jupyter@googlegroups.com>

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
RUN apt-get update \
  && apt-get install -y -q \
    build-essential \
    gcc \
    git \
    libcurl4-openssl-dev \
    libmemcached-dev \
    libsqlite3-dev \
    libzmq3-dev \
    make \
    nodejs \
    nodejs-legacy \
    npm \
    pandoc \
    python3-dev \
    python3-pip \
    sqlite3 \
    zlib1g-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
  && pip3 install --upgrade setuptools pip \
  && hash -r \
  && pip3 install --no-cache-dir invoke


# To change the number of threads use
# docker run -d -e NBVIEWER_THREADS=4 -p 80:8080 nbviewer
ENV NBVIEWER_THREADS 2
EXPOSE 8080

WORKDIR /srv/nbviewer

# asset toolchain
ADD ./package.json /srv/nbviewer/
RUN npm install .

# python requirements
ADD ./requirements.txt /srv/nbviewer/
RUN pip3 install --no-cache-dir --upgrade -r requirements.txt && \
    pip3 freeze

# tasks will likely require re-running everything
ADD ./tasks.py /srv/nbviewer/

# front-end dependencies
ADD ["./nbviewer/static/bower.json", "./nbviewer/static/.bowerrc", \
     "/srv/nbviewer/nbviewer/static/"]

# RUN invoke bower
WORKDIR /srv/nbviewer/nbviewer/static
RUN ../../node_modules/.bin/bower install \
  --allow-root \
  --config.interactive=false

WORKDIR /srv/nbviewer

# build css
ADD . /srv/nbviewer/
RUN invoke less

# Expose volume
# docker run -p 8080:8080 -v /host/directory:/srv/notebooks nbviewer
RUN mkdir /srv/notebooks
VOLUME /srv/notebooks

# root up until now!
USER nobody

CMD ["python3", "-m", "nbviewer", "--port=8080", "--localfiles=/srv/notebooks"]
