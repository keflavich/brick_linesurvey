import numpy as np
from astropy import units as u
from astroquery.alma import Alma, utils
import pylab as pl

from scipy.ndimage import label

Alma.query({'project_code':'2019.1.00092.S'})
rslt = Alma.query({'project_code':'2019.1.00092.S'}, public=False, cache=False)

cov = np.linspace(80, 350, 4000)*u.GHz

delivered = np.zeros(cov.size, dtype='bool')
taken = np.zeros(cov.size, dtype='bool')

for row in rslt:
    fsupp = utils.parse_frequency_support(row['Frequency support'])
    for low,hi in fsupp:
        delivered |= (cov > low) & (cov < hi) & bool(row['Release date'])
        taken |= (cov > low) & (cov < hi) & (not bool(row['Release date']))

pl.clf()

chunks,nchunks = label(delivered)
for ii in range(1, nchunks+1):
    cov_match = chunks == ii
    xmin, xmax = cov[cov_match].min(), cov[cov_match].max()
    blubox = pl.fill_between(u.Quantity([xmin, xmax]), 0, 1, color='b', alpha=0.75)

chunks,nchunks = label(taken)
for ii in range(1, nchunks+1):
    cov_match = chunks == ii
    xmin, xmax = cov[cov_match].min(), cov[cov_match].max()
    obox = pl.fill_between(u.Quantity([xmin, xmax]), 0, 1, color='orange', alpha=0.75)

#pl.plot(cov, delivered, label='Delivered')
#pl.plot(cov, taken, label='Observed')
pl.xlabel("Frequency (GHz)")
pl.ylabel("Covered?")
pl.yticks([])
#pl.legend(loc='best')
pl.savefig("coverage.png")
