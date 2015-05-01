# Using the Ubuntu image
FROM ipython/ipython:3.x

MAINTAINER IPython Project <ipython-dev@scipy.org>

RUN apt-get install -y -q \
  libmemcached-dev

# To change the number of threads use
# docker run -d -e NBVIEWER_THREADS=4 -p 80:8080 nbviewer
ENV NBVIEWER_THREADS 2
EXPOSE 8080

RUN pip install invoke && \
    pip3 install invoke
WORKDIR /srv/nbviewer

# asset toolchain
ADD ./package.json /srv/nbviewer/
RUN npm install .

ADD ./requirements.txt /srv/nbviewer/
RUN pip install -r requirements.txt && \
    pip3 install -r requirements.txt

ADD ./tasks.py /srv/nbviewer/

ADD ["./nbviewer/static/bower.json", "./nbviewer/static/.bowerrc", \
     "/srv/nbviewer/nbviewer/static/"]
RUN invoke bower

ADD . /srv/nbviewer/
RUN invoke less

USER nobody

CMD ["python3", "-m", "nbviewer", "--port=8080"]
