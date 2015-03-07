# Using the Ubuntu image
FROM ipython/ipython:3.x

MAINTAINER IPython Project <ipython-dev@scipy.org>

RUN apt-get install -y -q \
  libmemcached-dev

# To change the number of threads use
# docker run -d -e NBVIEWER_THREADS=4 -p 80:8080 nbviewer
ENV NBVIEWER_THREADS 2
EXPOSE 8080

# Install asset toolchain: if you change your build, go pretty far back
ADD ./package.json /srv/nbviewer/
RUN npm install .

# Install local automation
ADD ./tasks.py /srv/nbviewer/

ADD ["./nbviewer/static/bower.json", "./nbviewer/static/.bowerrc", \
     "/srv/nbviewer/nbviewer/static/"]
RUN invoke bower

ADD . /srv/nbviewer/
RUN invoke less

USER nobody

CMD ["python", "-m", "nbviewer", "--port=8080"]
