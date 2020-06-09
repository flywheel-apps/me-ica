import datetime
import json
import logging
import os
from os import path as op
from pathlib import Path
import psutil
import shutil
import subprocess as sp
import zipfile

import flywheel


logging.basicConfig()
log = logging.getLogger(__name__)


meica_call_dict = ("MNI",
                    "qwarp",
                    "native",
                    "space",
                    "fres",
                    "no_skullstrip",
                    "no_despike",
                    "no_axialize",
                    "mask_mode",
                    "coreg_mode",
                    "strict",
                    "smooth",
                    "align_base",
                    "TR",
                    "tpattern",
                    "align_args",
                    "ted_args",
                    "select_only",
                    "tedica_only",
                    "export_only",
                    "daw",
                    "tlrc",
                    "highpass",
                    "detrend",
                    "initcost",
                    "finalcost",
                    "sourceTEs",
                    "prefix",
                    "cpus",
                    "label",
                    "test_proc",
                    "script_only",
                    "pp_only",
                    "keep_int",
                    "skip_check",
                    "RESUME",
                    "OVERWRITE")


def generate_call(config_dict):
    """ Generate the second half of the MEICA call
        
    This function loops
    through all the keys in the config dictionary, and matches them to the keys in
    meica_call_dict.  If the key is present in meica_call_dict, the value from
    config_dict is used as the value for that key.  These keys are usd to build the
    second half of the command call to run meica.  This call is returned as a string.
    
    Args:
        config_dict (dict): The dictionary in the flywheel gear context "context.config"
        that has all the configuration options set in the manifest.

    Returns:
        command_tail (str): The second half of the command call used to run meica.

    """
    # this generates everything that comes in the meica.py call after the dataset and echo times
    command_tail = ""
    for key in meica_call_dict:
        log.debug('Checking Key {}'.format(key))
        if key in config_dict:
            log.debug('\tIn Config')
            if isinstance(config_dict[key], bool) and config_dict[key]:
                log.debug('\tBool In Config adding key')
                command_tail += '--{} '.format(key)
            elif not isinstance(config_dict[key], bool) and config_dict[key] != "":
                log.debug('\tVal In Config adding key/value')
                command_tail += '--{} {} '.format(key, config_dict[key])

    return (command_tail)


def set_environment(environ_json='/tmp/gear_environ.json'):
    """ Loads environment variables saved as a .json file into the current environment.
    
    Flywheel gears do not retain environmental settings when run on a flywheel instance.
    Thus, any environment setup performed in the dockerfile is lost.  As a workaround,
    these environmental variables are saved as a .json file as a final step in docker
    image creation.  By convention, this file is saved as '/tmp/gear_environ.json'.
    
    Args:
       environ_json (str or os.PathLike object): The location of a .json file containing
       the environment variables to be loaded.
    
    """
    
    # Let's ensure that we have our environment .json file and load it up
    if op.exists(environ_json):
    
        # If it exists, read the file in as a python dict with json.load
        with open(environ_json, 'r') as f:
            log.info('Loading gear environment')
            environ = json.load(f)
    
        # Now set the current environment using the keys.  This will automatically be used with any
        # sp.run() calls, without the need to pass "env=" into sp.run(), as in:
        #  sp.run(<command>, env=<environment dictionary>) 
        # https://docs.python.org/3/library/subprocess.html#subprocess.run
        # Passing "env=" would unset all these variables, so you must leave it out of any sp.run() 
        # calls
        
        for key in environ.keys():
            log.debug('{}: {}'.format(key, environ[key]))
            os.environ[key] = environ[key]
    else:
        log.error('No Environment file found!')
        log.warning('It is unlikely that this gear will be able to run without an environment file')
        log.warning('Save the environment in the docker image using the following command:')
        
        raise Exception
    
    return


def run_meica_call(command, output_directory):
    """ Runs the MEICA afni command constructed by this program
    
    This calls the bash command generated in this program.  The return code is evaluated
    to inform how this function exits.  If there is an error (return code != 0), log an
    error message and return the return code.  Otherwise, simply return the return code.
    An exception is not raised so that program flow can be controlled at a higher level.
    
    Args:
        command (str): the bash command call in string format (not list).  Afni is run
        with shell=True because it's a pain to get working otherwise.
        output_directory (str): a working directory that this function navigates to, to
        catch any output.
    Returns:
        returncode (int): the returncode of the command call.

    """
    # We need to be operating in the output directory.
    log.debug('Changed working directory to {}'.format(output_directory))
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
        log.error('Error executing main processing script.')
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


def setup_input_data(acquisition_id, api_key, output_directory='/flywheel/v0/output'):
    """For a given input dicom file, grab all of the nifti files from that acquisition.
    
    It's more convenient for a user to select one input file than three (or potentially
    more in the case of multi-echo fMRI).  To this end, the user only has to select the
    original dicom that the multi echo nifti files came from.  The sdk then explores the
    dicom's acquisition container, looking for the associated nifti files.  These are
    downloaded and returned as a list of paths to the file.

    
    
    Args:
        acquisition_id (str): the unique flywheel ID of the acquisition containing the
        nifti files to load
        api_key (str): the api key needed to access this data.
        output_directory (str): the output directory, intended to be the "flywheel"
        output directory that returns its data to the analysis container.  This is where
        the nifti files are downloaded to.  They're stored this way so that the user can
        see exactly which files were used, since only a dicom is specified at the input.

    Returns:
        datasets (list): an ordered list of path locations, one element for each nifti
        file.
        tes (list): an ordered list of te's , where the order is associated with the
        nifti files specified in the datasets list.
    """

    # Flywheel Object
    fw = flywheel.Client(api_key)

    # For this acquisition find each nifti file, download it and note its echo time
    acquisition = fw.get_acquisition(acquisition_id)
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
        
        # IDEA:  Handle case where EchoTime is not here
        # or classification is not correct
        # Or not multi echo data
        # Or if coronavirus attack
        
        # Append a dict containing the path and te of this nifti file for easy sorting
        meica_data.append({
            "path": n.name,
            "te": echo_time * 1000  # Convert to ms
        })

    # Generate prefix
    # The prefix of this command consists of multiple nifti files (one for each echo),
    # Followed by the te of each nifti file.  Since a single dicom is passed into the
    # gear, extra logic is needed to find the individual nifti files and automatically
    # exctract their TE's. Because meica_data is a list of path/te dictionary pairs,
    # a lamda function is used to sort them in order of their te.  That way, the files
    # are in order of lowest to highest te, where meica_data[0] is lowest, and
    # meica_data[-1] is highest.  The paths of the nifti files (ordered) and the te's
    # (also ordered) are returned as lists, as it's more convenient to use them in that
    # form later in the program.
    
    sub_code = fw.get_session(acquisition.parents.session).subject.code.strip().replace(' ', '')
    label = acquisition.label.strip().replace(' ', '')
    prefix = '%s_%s' % (sub_code, label)

    meica_data = sorted(meica_data, key=lambda k: k['te'])
    datasets = [Path(meica['path']) for meica in meica_data]
    tes = [meica['te'] for meica in meica_data]

    return (datasets, tes)


def log_system_resources(log):
    """Log system resource information
    
    Log system resource information to help with debugging.  In the event of job failure, it should
    be verified that there was sufficient memory to complete the task.
    
    Args:
        log (logging.Logger): the log being used in this script

    """
    log.info(
        'Logging System Resources\n\n==============================================================================\n')
    try:
        log.info('CPU Count: \t %s', psutil.cpu_count())
        log.info('CPU Speed: \t %s', psutil.cpu_freq())
        log.info('Virtual Memory: \t %s', psutil.virtual_memory())
        log.info('Swap Memory: \t %s', psutil.swap_memory())
        log.info('Disk Usage: \t %s', psutil.disk_usage('/'))
    except Exception as e:
        log.warning('Error Logging system info. Attempted to retrieve the following: CPU Count,'
                    ' CPU Speed, Virtual Memory, Swap Memory, Disk Usage')

    log.info('\n\n==============================================================================\n')


def setup_environment():
    """Set up the program environment
    
    Sets up the logger at the desired log level, logs the start time of the gear, logs
    the system resources, and sets up environmental variables
    
    Returns:
        context (flywheel.gear_context.GearContext): the gear context

    """
    context = flywheel.gear_context.GearContext()
    log.setLevel(getattr(logging, context.config['gear-log-level']))
    log.info('  start: %s' % datetime.datetime.utcnow())
    log_system_resources(log)
    set_environment()
    
    return(context)



def create_meica_call(datasets, tes, config, output_directory, context):
    """Create the bash MEICA call
    
    
    Create the bash MEICA call used by AFNI to perform multi-echo analysis.
    Args:
        datasets (list): an ordered list of paths to the nifti files being used in the 
        analysis.  Order must match the order of te's in the "te" input list
        tes (list): an ordered list of te's associated with the nifti files in
        "datasets"
        config (dict): the gear config settings
        output_directory (str): the output directory of the flywheel gear
        context (flywheel.gear_context.GearContext): the gear context

    Returns:
        command (str): The bash command to be called.

    """
    
    if context.get_input_path('anatomical'):  # Optional
        anatomical_input = context.get_input_path('anatomical')
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


    # create the command head
    command_head = 'cd %s && /me-ica/meica.py %s %s -b %s %s ' % (output_directory, dataset_cmd,
                                                                  echo_cmd,
                                                                  basetime,
                                                                  anatomical_cmd)
    # Create the command tail
    command_tail = generate_call(config)
    
    # Append the two parts
    command = command_head + command_tail
    log.debug(command)
    
    return(command)

    
    
def cleanup(status, config, output_directory):
    """Cleanup output directory for easier viewing
    
    Cleanup the output directory by zipping folders/outputs for easy viewing/downloading on flywheel
    
    Args:
        status (int): the exit status of the MEICA call
        config (dict): the gear config settings
        output_directory (str): the output directory where the files are saved.


    """
    
    
    if status == 0 or config['flywheel_save_output_on_error']:

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
        os.system(cmd)

    log.info('Done: %s' % datetime.datetime.utcnow())

