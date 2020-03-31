#!/usr/bin/env python

import shlex
import subprocess
import json
import shutil
import psutil
import zipfile
import logging
import datetime
import flywheel
import os
import pprint
from collections import OrderedDict
from pathlib import Path
import subprocess as sp
import os.path as op

logging.basicConfig()
log = logging.getLogger(__name__)

meica_call_dict = OrderedDict()

meica_call_dict["MNI"] = ""
meica_call_dict["qwarp"] = ""
meica_call_dict["native"] = ""
meica_call_dict["space"] = ""
meica_call_dict["fres"] = ""
meica_call_dict["no_skullstrip"] = ""
meica_call_dict["no_despike"] = ""
meica_call_dict["no_axialize"] = ""
meica_call_dict["mask_mode"] = ""
meica_call_dict["coreg_mode"] = ""
meica_call_dict["strict"] = ""
meica_call_dict["smooth"] = ""
meica_call_dict["align_base"] = ""
meica_call_dict["TR"] = ""
meica_call_dict["tpattern"] = ""
meica_call_dict["align_args"] = ""
meica_call_dict["ted_args"] = ""
meica_call_dict["select_only"] = ""
meica_call_dict["tedica_only"] = ""
meica_call_dict["export_only"] = ""
meica_call_dict["daw"] = ""
meica_call_dict["tlrc"] = ""
meica_call_dict["highpass"] = ""
meica_call_dict["detrend"] = ""
meica_call_dict["initcost"] = ""
meica_call_dict["finalcost"] = ""
meica_call_dict["sourceTEs"] = ""
meica_call_dict["prefix"] = ""
meica_call_dict["cpus"] = ""
meica_call_dict["label"] = ""
meica_call_dict["test_proc"] = ""
meica_call_dict["script_only"] = ""
meica_call_dict["pp_only"] = ""
meica_call_dict["keep_int"] = ""
meica_call_dict["skip_check"] = ""
meica_call_dict["RESUME"] = ""
meica_call_dict["OVERWRITE"] = ""


def generate_call(config_dict):
    # this generates everything that comes in the meica.py call after the dataset and echo times
    command_tail = ""
    for key in meica_call_dict.keys():
        log.debug('Checking Key {}'.format(key))
        if key in config_dict:
            log.debug('\tIn Config')
            if isinstance(config_dict[key], bool) and config_dict[key]:
                log.debug('\tBool In Config adding key')
                command_tail += '--{} '.format(key)
            elif not isinstance(config_dict[key], bool) and config_dict[key] != "":
                log.debug('\tVal In Config addind key/value')
                command_tail += '--{} {} '.format(key, config_dict[key])

    return (command_tail)


def set_environment(environ_json='/tmp/gear_environ.json'):
    # Let's ensure that we have our environment .json file and load it up
    if op.exists(environ_json):

        # If it exists, read the file in as a python dict with json.load
        with open(environ_json, 'r') as f:
            log.info('Loading gear environment')
            environ = json.load(f)

        # Now set the current environment using the keys.  This will automatically be used with any sp.run() calls,
        # without the need to pass in env=...  Passing env= will unset all these variables, so don't use it if you do it
        # this way.
        for key in environ.keys():
            log.debug('{}: {}'.format(key, environ[key]))
            os.environ[key] = environ[key]
    else:
        log.warning('No Environment file found!')
    # Pass back the environ dict in case the run.py program has need of it later on.
    return environ


def run_afni_command(command, output_directory):
    # We need to be operating in the output directory.
    os.chdir(output_directory)

    # Print the command (also a test of the sp.Popen call)
    echo_command = ['echo']
    echo_command.extend(command.split())
    sp.Popen(echo_command)

    # Run the main command to build the processing script
    pr = sp.Popen(command, cwd=output_directory, shell=True)
    pr.wait()
    pr.communicate()
    if pr.returncode != 0:
        log.critical('Error executing main processing script.')
        return (pr.returncode)

    # If we make it here, pr.returncode is zero
    return (pr.returncode)
    # I'm going to keep using parenthesis around return statements.  I've been hurt before with 
    # Print statements from python2 -> 3, I'm not making that same mistake twice.


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

    # Little nested function to prepare the proper archive path
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


def get_meica_data(context, output_directory='/flywheel/v0/output'):
    """
    For a given input dicom file, grab all of the nifti files from that acquisition.

    Return MEICA data which is a sorted list of file objects.
    """

    # Flywheel Object
    fw = flywheel.Client(context.get_input('api_key')['key'])

    # For this acquisition find each nifti file, download it and note its echo time
    acquisition = fw.get_acquisition(context.get_input('functional')['hierarchy']['id'])
    nifti_files = [x for x in acquisition.files
                   if x.type == 'nifti'
                   and "Functional" in x.classification['Intent']
                   ]
    log.info('Found %d Functional NIfTI files in %s' % (len(nifti_files), acquisition.label))

    # Compile meica_data structure
    meica_data = []
    repetition_time = ''
    for n in nifti_files:
        file_path = os.path.join(output_directory, n.name)
        log.info('Downloading %s' % (n.name))
        fw.download_file_from_acquisition(acquisition.id, n.name, file_path)
        echo_time = n.info.get('EchoTime')

        # TODO: Handle case where EchoTime is not here
        # or classification is not correct
        # Or not multi echo data
        # Or if coronavirus attack

        meica_data.append({
            "path": n.name,
            "te": echo_time * 1000  # Convert to ms
        })

    # Generate prefix
    sub_code = fw.get_session(acquisition.parents.session).subject.code.strip().replace(' ', '')
    label = acquisition.label.strip().replace(' ', '')
    prefix = '%s_%s' % (sub_code, label)

    meica_data = sorted(meica_data, key=lambda k: k['te'])
    datasets = [Path(meica['path']) for meica in meica_data]
    tes = [meica['te'] for meica in meica_data]

    return (datasets, tes)


def log_system_resources(log):
    log.info(
        'Logging System Resources\n\n==============================================================================\n')
    try:
        log.info('CPU Count: \t %s', psutil.cpu_count())
        log.info('CPU Speed: \t %s', psutil.cpu_freq())
        log.info('Virtual Memory: \t %s', psutil.virtual_memory())
        log.info('Swap Memory: \t %s', psutil.swap_memory())
        log.info('Disk Usage: \t %s', psutil.disk_usage('/'))
    except Exception as e:
        log.warning('Error Logging system info.  Attempted to retrieve the following:')
        log.info('CPU Count')
        log.info('CPU Speed')
        log.info('Virtual Memory')
        log.info('Swap Memory')
        log.info('Disk Usage')

    log.info('\n\n==============================================================================\n')


if __name__ == '__main__':
    """
    Run meica on a given dataset.
    """

    context = flywheel.gear_context.GearContext()
    config = context.config

    log.setLevel(getattr(logging, 'DEBUG'))
    logging.getLogger('MEICA').setLevel(logging.INFO)
    log.info('  start: %s' % datetime.datetime.utcnow())

    log_system_resources(log)
    environ = set_environment()

    ############################################################################
    # READ CONFIG
    config = context.config

    ############################################################################
    # FIND AND DOWNLOAD DATA
    output_directory = '/flywheel/v0/output'
    datasets, tes = get_meica_data(context, output_directory)

    ############################################################################
    # INPUTS

    anatomical_input = context.get_input_path('anatomical')
    if anatomical_input:  # Optional
        # Anatomical nifti must be in the output directory when running meica
        anatomical_nifti = os.path.join(output_directory, os.path.basename(anatomical_input))
        shutil.copyfile(anatomical_input, anatomical_nifti)
        log.info('anatomical_nifti: {}'.format(anatomical_nifti))
    else:
        anatomical_nifti = ''

    if context.get_input_path('slice_timing'):  # Optional
        slice_timing_input = context.get_input_path('slice_timing')

        # File must be in the output directory when running meica
        slice_timing_file = os.path.join(output_directory, os.path.basename(slice_timing_input))
        shutil.copyfile(slice_timing_input, slice_timing_file)
        config['tpattern'] = slice_timing_file
    else:
        slice_timing_input = ''

    basetime = config['basetime']

    ############################################################################
    # RUN MEICA

    dataset_cmd = '-d %s' % (','.join([str(x) for x in datasets]))
    echo_cmd = '-e %s' % (','.join([str(x) for x in tes]))
    anatomical_cmd = '-a %s' % (os.path.basename(anatomical_nifti)) if anatomical_nifti else ''


    # Run the command

    command_head = 'cd %s && /me-ica/meica.py %s %s -b %s %s ' % (output_directory, dataset_cmd,
                                                                  echo_cmd,
                                                                  basetime,
                                                                  anatomical_cmd)

    command_tail = generate_call(config)

    command = command_head + command_tail

    log.debug(command)
    os.chdir(output_directory)
    log.debug('Changed working directory to {}'.format(output_directory))
    status = run_afni_command(command, output_directory)

    if status == 0 or context.config['flywheel_save_output_on_error']:

        if not config['script_only']:
            log.info('Command exited with {} status. Compressing outputs...'.format(status))
            dirs = [os.path.join(output_directory, x)
                    for x in os.listdir(output_directory)
                    if os.path.isdir(os.path.join(output_directory, x))
                    ]
            for d in dirs:
                out_zip = os.path.join(output_directory, os.path.basename(d) + '.zip')
                log.info('Generating %s... ' % (out_zip))
                zipdir(d, out_zip, os.path.basename(d))
                shutil.rmtree(d)
        else:
            log.info('Command exited with 0 status.  Only the meica run script was generated.')

    else:
        log.info('ME-ICA crashed, and outputs were not saved')
        log.info(
            'To save outputs on crash, check "flywheel_save_output_on_error" in the config options')
        cmd = '/bin/rm -rf /flywheel/v0/output/*'
        os.system(command)

    log.info('Done: %s' % datetime.datetime.utcnow())

    os.sys.exit(status)
