# Create a base docker container that will run ME-ICA
#

FROM neurodebian:xenial
MAINTAINER Flywheel <support@flywheel.io>


# Install dependencies
RUN echo deb http://neurodeb.pirsquared.org data main contrib non-free >> /etc/apt/sources.list.d/neurodebian.sources.list
RUN echo deb http://neurodeb.pirsquared.org xenial main contrib non-free >> /etc/apt/sources.list.d/neurodebian.sources.list
RUN apt-get update \
    && apt-get install -y afni \
                          python \
                          git \
                          python-numpy \
                          python-scipy

RUN apt-get install -y python-pip && \
      pip install --upgrade flywheel-sdk

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}
COPY run ${FLYWHEEL}/run
COPY run_meica.py ${FLYWHEEL}/run_meica.py
RUN chmod +x ${FLYWHEEL}/*
COPY manifest.json ${FLYWHEEL}/manifest.json


# Configure entrypoint
ENTRYPOINT ["/flywheel/v0/run"]
