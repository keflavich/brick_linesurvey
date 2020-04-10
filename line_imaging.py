"""
Line imaging script.  There needs to be a to_image.json file in the directory
this is run in.  The to_image.json file is produced by the split_windows.py
script.

You can set the following environmental variables for this script:
    CHANCHUNKS=<number>
        The chanchunks parameter for tclean.  Depending on the version, it may
        be acceptable to specify this as -1, or it has to be positive.  This is
        the number of channels that will be imaged all at once; if this is too
        large, the data won't fit into memory and CASA will crash.
    BAND_NUMBERS=<band(s)>
        Image this/these bands.  Can be "3", "6", or "3,6" (no quotes)
    LOGFILENAME=<name>
        Optional.  If specified, the logger will use this filenmae
"""

import json
import os
import numpy as np
import astropy.units as u
from astropy import constants
try:
    from tasks import tclean, uvcontsub, impbcor
    from taskinit import casalog
    from tasks import exportfits
except ImportError:
    # futureproofing: CASA 6 imports this way
    from casatasks import tclean, uvcontsub, impbcor
    from casatasks import casalog
    from casatasks import exportfits
from parse_contdotdat import parse_contdotdat, freq_selection_overlap
from metadata_tools import determine_imsize, determine_phasecenter, is_7m, logprint
from imaging_parameters import line_imaging_parameters, selfcal_pars, line_parameters
from taskinit import msmdtool, iatool, mstool
from metadata_tools import effectiveResolutionAtFreq
from getversion import git_date, git_version
msmd = msmdtool()
ia = iatool()
ms = mstool()

if os.getenv('LOGFILENAME'):
    casalog.setlogfile(os.path.join(os.getcwd(), os.getenv('LOGFILENAME')))

imaging_root = "imaging_results"
if not os.path.exists(imaging_root):
    os.mkdir(imaging_root)


# set the 'chanchunks' parameter globally.
# CASAguides recommend chanchunks=-1, but this resulted in: 2018-09-05 23:16:34     SEVERE  tclean::task_tclean::   Exception from task_tclean : Invalid Gridding/FTM Parameter set : Must have at least 1 chanchunk
chanchunks = os.getenv('CHANCHUNKS') or 16

# global default: only do robust 0 for lines
robust = 0

vis = os.getenv('VIS')
if vis is None:
    raise ValueError("VIS not specified")

logprint("Running on vis {0}".format(vis))

ms.open(vis)
spwinfo = ms.getspectralwindowinfo()
spw_list = spwinfo.keys()
logprint("SPWs are {0}".format(spw_list))

field = 'BrickMaser'

for spw in spw_list:
    restfreq = spwinfo[spw]['RefFreq']
    freqname = int(restfreq / 1e9)
    logprint("SPW {spw} has rest frequency {restfreq} = {freqname}".format(**locals()))

    lineimagename = os.path.join(imaging_root,
                                 "BrickMaser_{0}_spw{1}".format(freqname,
                                                                spw,))

    coosys, racen, deccen = determine_phasecenter(ms=vis, field=field)
    phasecenter = "{0} {1}deg {2}deg".format(coosys, racen, deccen)
    (dra, ddec, pixscale) = determine_imsize(ms=vis, field=field,
                                             phasecenter=(racen, deccen),
                                             spw=0, pixfraction_of_fwhm=1/4.,
                                             min_pixscale=0.1, # arcsec
                                            )
    imsize = [int(dra), int(ddec)]
    cellsize = ['{0:0.2f}arcsec'.format(pixscale)] * 2

    dirty_tclean_made_residual = False

        # calculate the channel width
    chanwidths = []
    msmd.open(vis)
    count_spws = len(msmd.spwsforfield(field))
    msmd.close()
    chanwidth = np.max([np.abs(
        effectiveResolutionAtFreq(vis,
                                  spw='{0}'.format(ii),
                                  freq=restfreq*u.Hz,
                                  kms=True).max()) for ii in
        spw_list])
    chanwidths.append(chanwidth)
    chanwidth = np.mean(chanwidths)
    logprint("Channel widths were {0}, mean = {1}".format(chanwidths,
                                                          chanwidth),
             origin="almaimf_line_imaging")

    impars = {
            'niter': 100000,
            'robust': 0.0,
            'weighting': 'briggs',
            'scales': [0,3,9,],
            'gridder': 'standard',
            'specmode': 'cube',
            'deconvolver': 'multiscale',
            'outframe': 'LSRK',
            'veltype': 'radio',
            #'sidelobethreshold': 2.0,
            #'noisethreshold': 5.0,
            #'usemask': 'auto-multithresh',
            'threshold': '5sigma',
            'interactive': False,
            'pblimit': 0.2,
            'nterms': 1,
            'spw': spw,
            'field': field,
           }
    impars['chanchunks'] = chanchunks

    impars['imsize'] = imsize
    impars['cell'] = cellsize
    impars['phasecenter'] = phasecenter
    #impars['field'] = [field.encode()]*len(vis)


    # start with cube imaging

    if not os.path.exists(lineimagename+".image") and not os.path.exists(lineimagename+".residual"):
        if os.path.exists(lineimagename+".psf"):
            logprint("WARNING: The PSF for {0} exists, but no image exists."
                     "  This likely implies that an ongoing or incomplete "
                     "imaging run for this file exists.  It will not be "
                     "imaged this time; please check what is happening.  "
                     "(this warning issued /before/ dirty imaging)"
                     .format(lineimagename),
                     origin='almaimf_line_imaging')
            continue
        # first iteration makes a dirty image to estimate the RMS
        impars_dirty = impars.copy()
        impars_dirty['niter'] = 0

        logprint("Dirty imaging parameters are {0}".format(impars_dirty),
                 origin='almaimf_line_imaging')
        tclean(vis=vis,
               imagename=lineimagename,
               restoringbeam='', # do not use restoringbeam='common'
               # it results in bad edge channels dominating the beam
               **impars_dirty
              )
        for suffix in ('image', 'residual', 'model'):
            ia.open(lineimagename+"."+suffix)
            ia.sethistory(origin='almaimf_line_imaging',
                          history=["{0}: {1}".format(key, val) for key, val in
                                   impars_dirty.items()])
            ia.sethistory(origin='almaimf_line_imaging',
                          history=["git_version: {0}".format(git_version),
                                   "git_date: {0}".format(git_date)])
            ia.close()

        if os.path.exists(lineimagename+".image"):
            # tclean with niter=0 is not supposed to produce a .image file,
            # but if it does (and it appears to have done so on at
            # least one run), we still want to clean the cube
            dirty_tclean_made_residual = True
    elif not os.path.exists(lineimagename+".residual"):
        raise ValueError("The residual image is required for further imaging.")
    else:
        logprint("Found existing files matching {0}".format(lineimagename),
                 origin='almaimf_line_imaging'
                )

    if os.path.exists(lineimagename+".psf") and not os.path.exists(lineimagename+".image"):
        logprint("WARNING: The PSF for {0} exists, but no image exists."
                 "  This likely implies that an ongoing or incomplete "
                 "imaging run for this file exists.  It will not be "
                 "imaged this time; please check what is happening."
                 "(warning issued /after/ dirty imaging)"
                 .format(lineimagename),
                 origin='almaimf_line_imaging')
        # just skip the rest here - that means no contsub imaging
        continue

    # the threshold needs to be computed if any imaging is to be done (either contsub or not)
    # no .image file is produced, only a residual
    logprint("Computing residual image statistics for {0}".format(lineimagename), origin='almaimf_line_imaging')
    ia.open(lineimagename+".residual")
    stats = ia.statistics(robust=True)
    rms = float(stats['medabsdevmed'] * 1.482602218505602)
    ia.close()

    continue_imaging = False
    if 'threshold' in impars:
        if 'sigma' in impars['threshold']:
            nsigma = int(impars['threshold'].strip('sigma'))
            threshold = "{0:0.4f}Jy".format(nsigma*rms) # 3 rms might be OK in practice
            logprint("Threshold used = {0} = {2}x{1}".format(threshold, rms, nsigma),
                     origin='almaimf_line_imaging')
            impars['threshold'] = threshold
        else:
            threshold = impars['threshold']
            nsigma = (u.Quantity(threshold) / rms).to(u.Jy).value
            logprint("Manual threshold used = {0} = {2}x{1}"
                     .format(threshold, rms, nsigma),
                     origin='almaimf_line_imaging')

        if u.Quantity(threshold).to(u.Jy).value < stats['max']:
            # if the threshold was not reached, keep cleaning
            continue_imaging = True

    if continue_imaging or dirty_tclean_made_residual or not os.path.exists(lineimagename+".image"):
        # continue imaging using a threshold

        logprint("Imaging parameters are {0}".format(impars),
                 origin='almaimf_line_imaging')
        tclean(vis=vis,
               imagename=lineimagename,
               restoringbeam='', # do not use restoringbeam='common'
               # it results in bad edge channels dominating the beam
               **impars
              )
        for suffix in ('image', 'residual', 'model'):
            ia.open(lineimagename+"."+suffix)
            ia.sethistory(origin='almaimf_line_imaging',
                          history=["{0}: {1}".format(key, val) for key, val in
                                   impars.items()])
            ia.sethistory(origin='almaimf_line_imaging',
                          history=["git_version: {0}".format(git_version),
                                   "git_date: {0}".format(git_date)])
            ia.close()

        impbcor(imagename=lineimagename+'.image',
                pbimage=lineimagename+'.pb',
                outfile=lineimagename+'.image.pbcor', overwrite=True)

        exportfits(lineimagename+".image", lineimagename+".image.fits",
                   overwrite=True)
        exportfits(lineimagename+".image.pbcor", lineimagename+".image.pbcor.fits",
                   overwrite=True)



    logprint("Completed {0}".format(vis), origin='almaimf_line_imaging')


    logprint("Completed line_imaging.py run", origin='almaimf_line_imaging')
