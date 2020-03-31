# flywheel/me-ica
[Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) to enable the execution of [Multi-Echo ICA](https://me-ica.readthedocs.io/en/latest/).

## Introduction
Multi-Echo Independent Components Analysis (ME-ICA) is a method for fMRI analysis and denoising based on the T2* decay of BOLD signals, as measured using multi-echo fMRI. ME-ICA decomposes multi-echo fMRI datasets into independent components (ICs) using FastICA, then categorizes ICs as BOLD or noise using their BOLD and non-BOLD weightings (measured as Kappa and Rho values, respectively). Removing non-BOLD weighted components robustly denoises data for motion, physiology and scanner artifacts, in a simple and physically principled way <sup>[ref](https://github.com/ME-ICA/me-ica/blob/master/README.meica)</sup>. For more information, see:

  > Kundu, P., Inati, S.J., Evans, J.W., Luh, W.M. & Bandettini, P.A. Differentiating BOLD and non-BOLD signals in fMRI time series using multi-echo EPI. NeuroImage (2011).


``meica`` preprocesses multi-echo datasets and applies multi-echo ICA based on spatially concatenated echoes. It does so in the following steps:

1. Calculates motion parameters based on images with highest contrast (usually the first echo)
2. Applies motion correction and T2*-weighted co-registration parameters
3. Applies standard EPI preprocessing (slice-time correction, etc.)
4. Computes PCA and ICA in conjunction with TE-dependence analysis

##  Derivatives
  * ``medn``
      'Denoised' BOLD time series after: basic preprocessing,
      T2* weighted averaging of echoes (i.e. 'optimal combination'),
      ICA denoising.
      Use this dataset for task analysis and resting state time series correlation analysis.
  * ``tsoc``
      'Raw' BOLD time series dataset after: basic preprocessing
      and T2* weighted averaging of echoes (i.e. 'optimal combination').
      'Standard' denoising or task analyses can be assessed on this dataset
      (e.g. motion regression, physio correction, scrubbing, etc.)
      for comparison to ME-ICA denoising.
  * ``*mefc``
      Component maps (in units of \delta S) of accepted BOLD ICA components.
      Use this dataset for ME-ICR seed-based connectivity analysis.
  * ``mefl``
      Component maps (in units of \delta S) of ALL ICA components.
  * ``ctab``
      Table of component Kappa, Rho, and variance explained values, plus listing of component classifications.


## Flywheel Usage notes
This Analysis Gear will execute ME-ICA within the Flywheel platform on multi-echo functional data within a given acquisition.

*Please read and understand the following considerations prior to running the Gear on your data.*

### Input
* The user must provide a single input file (DICOM archive containing multi-echo data) from the acquisition on which they wish this Gear to run. The Gear will use that single input file to identify other data within that acquisition to use as input to the algorithm.
* The user may optionally provide an anatomical NIfTI file along with the functional input. This input, if provided, will be used for co-registration.

### Prior to Execution
* **Data within the acquisition must have a Classification set for each file.** The easiest way to do this is to run the `scitran/dicom-mr-classifer` Gear on those data prior to running the DICOM conversion Gear (dcm2niix). The "Classifier" Gear will set the input file's classification, upon which this Gear depends.

* **NIfTI files must be generated for data within the acquisition using the `scitran/dcm2niix` Gear (>=0.6)**. The `dcm2niix` Gear generates file metadata used to set the echo times and (importantly) derive slice timing for each of the given functional inputs. Slice timing information will subsequently be saved out as `slicetimes.txt`.

* **Please make sure that `subject code` and `session label` are set and valid prior to running the Gear.** The `prefix` configuration parameter is parsed from the `subject code` and  `session label` within Flywheel.

### Configuration
* Several configuration parameters can be set at runtime (see below). Please see the `manifest.json` file for the list of parameters and their options.

* **qwarp**: Nonlinear warp to standard space using QWarp (use --MNI or --space)  
* **native**: Output native space results in addition to standard space results  
* **space**: Path to specific standard space template for affine anatomical normalization  
* **fres**: Specify functional voxel dim. in mm (iso.) for resampling during preprocessing.   
* **no_skullstrip**: Anatomical is already intensity-normalized and skull-stripped (if -a provided)  
* **no_despike**: Do not de-spike functional data. Default is to de-spike, recommended.  
* **no_axialize**: Do not re-write dataset in axial-first order. Default is to axialize, recommended.  
* **mask_mode**: Mask functional with help from anatomical or standard space images: use 'anat' or 'template'  
* **coreg_mode**: Coregistration with Local Pearson and T2* weights (default), or use align_epi_anat.py (edge method): use 'lp-t2s' or 'aea'  
* **strict**: Hidden option.  Only modify if you're an expert user   
* **smooth**: FWData FWHM smoothing (3dBlurInMask). Default off. ex: --smooth 3mm  
* **align_base**: align_baExplicitly specify base dataset for volume registration  
* **TR**: The TR. Default read from input dataset header  
* **align_args**: Additional arguments to anatomical-functional co-registration routine  
* **ted_args**: Additional arguments to TE-dependence analysis routine  

* **select_only**: Hidden option.  Only modify if you're an expert user  
* **tedica_only**: Hidden option.  Only modify if you're an expert user  
* **export_only**: Hidden option.  Only modify if you're an expert user  
* **daw**: Hidden option.  Only modify if you're an expert user  
* **tlrc**: Hidden option.  Only modify if you're an expert user  
* **highpass**: Hidden option.  Only modify if you're an expert user  
* **detrend**: Hidden option.  Only modify if you're an expert user  
* **initcost**: Hidden option.  Only modify if you're an expert user  
* **finalcost**: Hidden option.  Only modify if you're an expert user  
* **sourceTEs**: Hidden option.  Only modify if you're an expert user  
  
* **prefix**: prefPrefix for final ME-ICA output datasets  
* **cpus**: cpMaximum number of CPUs (OpenMP threads) to use  
* **label**: labLabel to tag ME-ICA analysis folder.  
* **test_proc**: test_prAlign and preprocess 1 dataset then exit, for testing  
* **script_only**: script_onGenerate script only, then exit  
* **pp_only**: Preprocess only, then exit.  
* **keep_int**: Keep preprocessing intermediates. Default delete.  
* **skip_check**: Skip dependency checks during initialization.  
