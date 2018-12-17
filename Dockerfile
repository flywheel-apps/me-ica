# Create a base docker container that will run ME-ICA
#

FROM neurodebian:xenial
MAINTAINER Flywheel <support@flywheel.io>


# Install dependencies
RUN echo deb http://neurodeb.pirsquared.org data main contrib non-free >> /etc/apt/sources.list.d/neurodebian.sources.list \
    && echo deb http://neurodeb.pirsquared.org xenial main contrib non-free >> /etc/apt/sources.list.d/neurodebian.sources.list
RUN apt-get update \
    && apt-get install -y afni \
                          python \
                          git \
                          python-numpy \
                          python-scipy \
                          python-pip \
                          xvfb \
                          psmisc \
    && pip install --upgrade flywheel-sdk

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}
COPY run ${FLYWHEEL}/run
COPY run_meica.py ${FLYWHEEL}/run_meica.py
RUN chmod +x ${FLYWHEEL}/*
COPY manifest.json ${FLYWHEEL}/manifest.json

# Clone ME-ICA code from source
RUN git clone https://github.com/ME-ICA/me-ica.git

# Configure entrypoint
ENTRYPOINT ["/flywheel/v0/run"]
