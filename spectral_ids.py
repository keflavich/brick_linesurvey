from astroquery.splatalogue import Splatalogue, utils
from astropy import stats
from astropy import log
from astropy import constants
from astropy import units as u
from astropy import table
from astropy.table import Column
from scipy.ndimage import label
import numpy as np

import pyspeckit
import glob

results = []
Ulines = []

for fn in glob.glob("spectra/*.max.fits"):
    sp = pyspeckit.Spectrum(fn)

    med = np.nanmedian(sp.data)

    mad = stats.mad_std(sp.data - med)
    detections = (sp.data-med) > 5*mad

    labels, ct = label(detections)

    for labelid in range(1,ct+1):
        ssp = sp[labels == labelid]
        try:
            ssp.specfit()
            ssp.specfit.parinfo
            frq = ssp.specfit.parinfo['SHIFT0'].value * ssp.xarr.unit
        except Exception as ex:
            print(ex)
            frq = ssp.xarr.mean()
        sq = Splatalogue.query_lines(frq*(1+30/3e5), frq*(1+75/3e5),
                                     only_astronomically_observed=True)
        if len(sq) > 0:
            tbl = utils.minimize_table(sq)
            tbl.add_column(Column(data=u.Quantity((-(frq.to(u.GHz).value -
                                                     tbl['Freq']) / tbl['Freq']
                                                   * constants.c), u.km/u.s),
                                  name='Velocity'))
            results.append(tbl)
        else:
            log.warning(f"Frequency {frq.to(u.GHz)} had no hits")
            Ulines.append(frq)

match_table = table.unique(table.vstack(results))
match_table.sort('Freq')
match_table.write("line_fit_table.ipac", format='ascii.ipac', overwrite=True)
