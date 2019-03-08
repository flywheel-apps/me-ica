#!/usr/bin/env python

import os
import re
import csv
import json
import shutil
import string
import zipfile
import logging
import datetime
import flywheel
from pprint import pprint

logging.basicConfig()
log = logging.getLogger('MEICA')


def zipdir(dirPath=None, zipFilePath=None, includeDirInZip=True, deflate=True):
    """Create a zip archive from a directory.

    Note that this function is designed to put files in the zip archive with
    either no parent directory or just one parent directory, so it will trim any
    leading directories in the filesystem paths and not include them inside the
    zip archive paths. This is generally the case when you want to just take a
    directory and make it into a zip file that can be extracted in different
    locations.

    Keyword arguments:

    dirPath -- string path to the directory to archive. This is the only
    required argument. It can be absolute or relative, but only one or zero
    leading directories will be included in the zip archive.

    zipFilePath -- string path to the output zip file. This can be an absolute
    or relative path. If the zip file already exists, it will be updated. If
    not, it will be created. If you want to replace it from scratch, delete it
    prior to calling this function. (default is computed as dirPath + ".zip")

    includeDirInZip -- boolean indicating whether the top level directory should
    be included in the archive or omitted. (default True)

"""
    if deflate:
        mode = zipfile.ZIP_DEFLATED
    else:
        mode = zipfile.ZIP_STORED
    if not zipFilePath:
        zipFilePath = dirPath + ".zip"
    if not os.path.isdir(dirPath):
        raise OSError("dirPath argument must point to a directory. "
            "'%s' does not." % dirPath)
    parentDir, dirToZip = os.path.split(dirPath)
    #Little nested function to prepare the proper archive path
    def trimPath(path):
        archivePath = path.replace(parentDir, "", 1)
        if parentDir:
            archivePath = archivePath.replace(os.path.sep, "", 1)
        if not includeDirInZip:
            archivePath = archivePath.replace(dirToZip + os.path.sep, "", 1)
        return os.path.normcase(archivePath)

    outFile = zipfile.ZipFile(zipFilePath, "w", mode, allowZip64=True)
    for (archiveDirPath, dirNames, fileNames) in os.walk(dirPath):
        for fileName in fileNames:
            filePath = os.path.join(archiveDirPath, fileName)
            outFile.write(filePath, trimPath(filePath))
        # Make sure we get empty directories as well
        if not fileNames and not dirNames:
            zipInfo = zipfile.ZipInfo(trimPath(archiveDirPath) + "/")
            outFile.writestr(zipInfo, "")
    outFile.close()


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
    slice_timing = []
    repetition_time = ''
    for n in nifti_files:
        file_path = os.path.join(output_directory, n.name)
        log.info('Downloading %s' % (n.name))
        fw.download_file_from_acquisition(acquisition.id, n.name, file_path)
        echo_time = n.info.get('EchoTime')
        if not slice_timing:
            slice_timing = n.info.get('SliceTiming')
        if not repetition_time:
            repetition_time = n.info.get('RepetitionTime')
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

    # Tpattern_file
    if slice_timing:
        log.info('Generating slice timing information from input file metadata.')
        tpattern_file = os.path.join(output_directory, 'slicetimes.txt')
        with open(tpattern_file, 'w') as tf:
            for st in slice_timing:
                tf.write("%s " % st)
    else:
        tpattern_file = ''

    return sorted(meica_data, key=lambda k: k['te']), prefix, tpattern_file, repetition_time


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
    meica_data, prefix, tpattern_file, repetition_time = get_meica_data(config, output_directory)


    ############################################################################
    # INPUTS

    if config['inputs'].get('anatomical'): # Optional
        anatomical_input = config['inputs'].get('anatomical').get('location').get('path')

        # Anatomical nifti must be in the output directory when running meica
        anatomical_nifti = os.path.join(output_directory, os.path.basename(anatomical_input))
        shutil.copyfile(anatomical_input, anatomical_nifti)
    else:
        anatomical_nifti = ''

    if config['inputs'].get('slice_timing'): # Optional
        slice_timing_input = config['inputs'].get('slice_timing').get('location').get('path')

        # File must be in the output directory when running meica
        slice_timing_file = os.path.join(output_directory, os.path.basename(slice_timing_input))
        shutil.copyfile(slice_timing_input, slice_timing_file)
    else:
        slice_timing_input = ''


    ############################################################################
    # CONFIG OPTIONS

    basetime = config.get('config').get('basetime') # Default = "0"
    mni = config.get('config').get('mni') # Default = False
    tr = config.get('config').get('tr', '') # No default
    if not tr and repetition_time:
        tr = repetition_time
    cpus = config.get('config').get('cpus')
    no_axialize = config.get('config').get('no_axialize')
    native = config.get('config').get('native')
    keep_int = config.get('config').get('keep_int')
    tpattern_gen = config.get('config').get('tpattern_gen')


    ############################################################################
    # RUN MEICA

    dataset_cmd = '-d %s' % (','.join([ x['path'] for x in meica_data ]))
    echo_cmd = '-e %s' % (','.join([ str(x['te']) for x in meica_data ]))
    anatomical_cmd = '-a %s' % (os.path.basename(anatomical_nifti)) if anatomical_nifti else ''
    mni_cmd = '--MNI' if mni else ''
    tr_cmd = '--TR %s' % (str(tr)) if tr else ''
    cpus_cmd = '--cpus %s' % (str(cpus)) if cpus else ''
    no_axialize_cmd = '--no_axialize' if no_axialize else ''
    native_cmd = '--native' if native else ''
    keep_int_cmd = '--keep_int' if keep_int else ''
    if slice_timing_input:
        tpattern_cmd = '--tpattern=@%s' % (os.path.basename(slice_timing_input))
        log.info('Using user-provided slice-timing file...')
    else:
        tpattern_cmd = '--tpattern=@%s' % (tpattern_file) if tpattern_file and tpattern_gen else ''


    # Run the command
    command = 'cd %s && /flywheel/v0/me-ica/meica.py %s %s -b %s %s %s %s %s %s %s %s %s --prefix %s' % ( output_directory,
            dataset_cmd,
            echo_cmd,
            basetime,
            anatomical_cmd,
            mni_cmd,
            tr_cmd,
            cpus_cmd,
            no_axialize_cmd,
            native_cmd,
            keep_int_cmd,
            tpattern_cmd,
            prefix )

    log.info(command)
    status = os.system(command)

    if status == 0:
        log.info('Command exited with 0 status. Compressing outputs...')
        dirs = [ os.path.join(output_directory, x)
                        for x in os.listdir(output_directory)
                        if os.path.isdir(os.path.join(output_directory, x))
                ]
        for d in dirs:
            out_zip = os.path.join(output_directory, os.path.basename(d) + '.zip')
            log.info('Generating %s... ' % (out_zip))
            zipdir(d, out_zip, os.path.basename(d))
            shutil.rmtree(d)

    log.info('Done: %s' % datetime.datetime.utcnow())

    os.sys.exit(status)
