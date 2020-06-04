# Create a base docker container that will run ME-ICA

FROM dbp2123/afni:0.0.1_20.0.18
MAINTAINER Flywheel <support@flywheel.io>

ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}
COPY run_meica.py ${FLYWHEEL}/run_meica.py
COPY run.py ${FLYWHEEL}/run.py
RUN chmod +x ${FLYWHEEL}/run.py ${FLYWHEEL}/run_meica.py 
COPY manifest.json ${FLYWHEEL}/manifest.json
