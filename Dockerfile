# Define a builder image
FROM debian:jessie as builder

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
RUN apt-get update && \
  apt-get install -yq --no-install-recommends \
    curl \
    bzip2 \
    ca-certificates

ENV MINICONDA_VERSION 4.7.10
ENV PATH=/opt/conda/bin:$PATH
RUN cd /tmp && \
    curl -sSL https://repo.continuum.io/miniconda/Miniconda3-${MINICONDA_VERSION}-Linux-x86_64.sh -o /tmp/miniconda.sh && \
    echo "1c945f2b3335c7b2b15130b1b2dc5cf4 *miniconda.sh" | md5sum -c - && \
    /bin/bash miniconda.sh -f -b -p /opt/conda && \
    rm miniconda.sh && \
    /opt/conda/bin/conda config --system --prepend channels conda-forge && \
    /opt/conda/bin/conda config --system --set auto_update_conda false && \
    /opt/conda/bin/conda config --system --set show_channel_urls true && \
    /opt/conda/bin/conda install --quiet --yes conda="${MINICONDA_VERSION%.*}.*" && \
    /opt/conda/bin/conda update --all --quiet --yes && \
    conda clean -tipsy

# NodeJS toolchain
WORKDIR /srv/nbviewer
RUN conda install nodejs git
COPY ./package.json /srv/nbviewer/
RUN npm install .

# Python requirements
ADD ./requirements.txt /srv/nbviewer/
RUN conda install --file requirements.txt

# Add bower requirements
COPY [ \
  "./nbviewer/static/bower.json", \
  "./nbviewer/static/.bowerrc", \
  "/srv/nbviewer/nbviewer/static/" \
]

# Invoke bower
WORKDIR /srv/nbviewer/nbviewer/static
RUN ../../node_modules/.bin/bower install \
  --allow-root \
  --config.interactive=false

# Build CSS
WORKDIR /srv/nbviewer
RUN conda install invoke
COPY ./nbviewer/static/less /srv/nbviewer/nbviewer/static/less/
COPY ./tasks.py /srv/nbviewer/
RUN invoke less

# Remove build-only packages so that we can copy a clean conda environment
# to the runtime image. Need to leave git intact: it's a runtime dep!
RUN conda remove -y nodejs invoke && \
  conda clean -ay && \
  rm -rf /opt/conda/pkgs /opt/conda/conda-meta && \
  rm -rf /srv/nbviewer/node_modules /srv/nbviewer/notebook-*

# Copy source tree in and only keep .git so that the version
# web resource works properly
COPY . /srv/nbviewer

# Now define the runtime image
FROM debian:jessie

COPY --from=builder /opt/conda /opt/conda
COPY --from=builder /srv/nbviewer /srv/nbviewer

LABEL maintainer="Jupyter Project <jupyter@googlegroups.com>"

# To change the number of threads use
# docker run -d -e NBVIEWER_THREADS=4 -p 80:8080 nbviewer
ENV NBVIEWER_THREADS 2
ENV PATH=/opt/conda/bin:$PATH
WORKDIR /srv/nbviewer
EXPOSE 8080
USER nobody

EXPOSE 9000
CMD ["python", "-m", "nbviewer", "--port=8080"]
