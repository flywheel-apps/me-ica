#!/usr/bin/python3

import os
import run_meica

def main():
    
    # Setup the gear environment
    context = run_meica.setup_environment()
    config = context.config
    output_directory = context.output_dir
    
    # Setup the necessary input files
    datasets, tes = run_meica.setup_input_data(context.get_input('functional')['hierarchy']['id'],
                                               context.get_input('api_key')['key'],
                                               output_directory)
    
    # create the full command call from the inputs and config settings
    command = run_meica.create_meica_call(datasets, tes, config, output_directory, context)
    
    # Execute the command
    status = run_meica.run_meica_call(command, output_directory)
    
    # Cleanup, handle log messages regarding exit status (success or fail)
    run_meica.cleanup(status, config, output_directory)
    
    # Exit based on the status code.
    os.sys.exit(status)



if __name__=='__main__':
    main()