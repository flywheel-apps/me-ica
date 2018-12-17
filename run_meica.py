#!/usr/bin/env python

import os
import re
import csv
import json
import shutil
import string
import logging
import datetime
import flywheel
from pprint import pprint

logging.basicConfig()
log = logging.getLogger('MEICA')

def get_meica_data(config, output_directory='/flywheel/v0/output'):
    """
    For a given input dicom file, grab all of the nifti files from that acquisition.

    Return MEICA data which is a sorted list of file objects.
    """

    # Flywheel Object
    fw = flywheel.Flywheel(config['inputs']['api_key']['key'])

    # For this acquisition find each nifti file, download it and note its echo time
    acquisition = fw.get_acquisition(config['inputs'].get('functional').get('hierarchy').get('id'))
    nifti_files = [ x for x in acquisition.files
                        if x.type == 'nifti'
                        and "Functional" in x.classification['Intent']
                  ]
    log.info('Found %d Functional NIfTI files in %s' % (len(nifti_files), acquisition.label))

    # Compile meica_data structure
    meica_data = []
    for n in nifti_files:
        file_path = os.path.join(output_directory, n.name)
        log.info('Downloading %s' % (n.name))
        fw.download_file_from_acquisition(acquisition.id, n.name, file_path)
        echo_time = n.info.get('EchoTime')
        # TODO: Handle case where EchoTime is not here
        # or classification is not correct
        # Or not multi echo data

        meica_data.append({
                "path": n.name,
                "te": echo_time*1000 # Convert to ms
            })

    # Generate prefix
    sub_code = fw.get_session(acquisition.parents.session).subject.code.strip().replace(' ','')
    label = acquisition.label.strip().replace(' ','')
    prefix = '%s_%s' % (sub_code, label)

    return sorted(meica_data, key=lambda k: k['te']), prefix


if __name__ == '__main__':
    """
    Run meica on a given dataset.
    """

    import os
    import pprint
    import shlex
    import subprocess

    log.setLevel(getattr(logging, 'DEBUG'))
    logging.getLogger('MEICA').setLevel(logging.INFO)
    log.info('  start: %s' % datetime.datetime.utcnow())


    ############################################################################
    # READ CONFIG

    CONFIG_FILE_PATH = '/flywheel/v0/config.json'
    with open(CONFIG_FILE_PATH, 'r') as config_file:
        config = json.load(config_file)


    ############################################################################
    # FIND AND DOWNLOAD DATA

    output_directory = '/flywheel/v0/output'
    meica_data, prefix = get_meica_data(config, output_directory)


    ############################################################################
    # INPUTS

    if config['inputs'].get('anatomical'): # Optional
        anatomical_nifti = config['inputs'].get('anatomical').get('location').get('path')
    else:
        anatomical_nifti = ''


    ############################################################################
    # CONFIG OPTIONS

    basetime = config.get('config').get('basetime') # Default = "0"
    mni = config.get('config').get('mni') # Default = False


    ############################################################################
    # RUN MEICA

    dataset_cmd = '-d %s' % (','.join([ x['path'] for x in meica_data ]))
    echo_cmd = '-e %s' % (','.join([ str(x['te']) for x in meica_data ]))

    anatomical_cmd = '-a %s' % (anatomical_nifti) if anatomical_nifti else ''
    mni_cmd = '--MNI' if mni else ''

    command = 'cd %s && /flywheel/v0/me-ica/meica.py %s %s -b %s %s %s --prefix %s' % (
                output_directory, dataset_cmd, echo_cmd, basetime, anatomical_cmd, mni_cmd, prefix )

    log.info(command)
    status = os.system(command)

    if status == 0:
        log.info('Success. Compressing outputs...')
        dirs = [ os.path.join(output_directory, x)
                        for x in os.listdir(output_directory)
                        if os.path.isdir(os.path.join(output_directory, x))
                ]
        for d in dirs:
            out_zip = os.path.join(output_directory, os.path.basename(d))
            log.info('Generating %s... ' % (out_zip))
            shutil.make_archive(out_zip, 'zip', root_dir=output_directory, base_dir=os.path.basename(d), verbose=True)
            shutil.rmtree(d)

    log.info('Done: %s' % datetime.datetime.utcnow())

    os.sys.exit(status)
