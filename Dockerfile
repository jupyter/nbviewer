# Using the Ubuntu image
FROM ubuntu:14.04

MAINTAINER IPython Project <ipython-dev@scipy.org>

# Make sure apt is up to date
RUN apt-get update
RUN apt-get upgrade -y

# Not essential, but wise to set the lang
RUN apt-get install -y language-pack-en
ENV LANGUAGE en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

RUN locale-gen en_US.UTF-8
RUN dpkg-reconfigure locales

# Python binary dependencies, developer tools
RUN apt-get install -y -q build-essential make gcc zlib1g-dev git
RUN apt-get install -y -q python python-dev python-pip

# nbviewer binary dependencies
RUN apt-get install -y -q libzmq3-dev sqlite3 libsqlite3-dev pandoc libevent-dev libcurl4-openssl-dev libmemcached-dev nodejs nodejs-legacy npm

# install IPython 3.x branch
WORKDIR /srv
RUN git clone --depth 1 -b 3.x https://github.com/ipython/ipython.git
WORKDIR /srv/ipython
RUN git submodule init && git submodule update
RUN pip install -e .[notebook]

RUN pip install invoke
WORKDIR /srv/nbviewer

# asset toolchain
ADD ./package.json /srv/nbviewer/
RUN npm install .

ADD ./requirements.txt /srv/nbviewer/
RUN pip install -r requirements.txt

ADD ./tasks.py /srv/nbviewer/

ADD ["./nbviewer/static/bower.json", "./nbviewer/static/.bowerrc", \   
     "/srv/nbviewer/nbviewer/static/"]
RUN invoke bower

EXPOSE 8080

ADD . /srv/nbviewer/
RUN invoke less

# To change the number of threads use
# docker run -d -e NBVIEWER_THREADS=4 -p 80:8080 nbviewer
ENV NBVIEWER_THREADS 2

USER nobody

CMD ["python","-m","nbviewer","--port=8080"]
