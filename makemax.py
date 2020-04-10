import os
import glob
from spectral_cube import SpectralCube
from spectral_cube.dask_spectral_cube import DaskSpectralCube

import time

for suffix in ("image.pbcor.fits",):
    for fn in glob.glob(f"BrickMaser*{suffix}"):
        t0 = time.time()
        if not os.path.exists(f'spectra/{fn.replace("{suffix}","max.fits")}'):
            #cube = SpectralCube.read(fn)
            #print(cube)
            #mxspec = cube.max(axis=(1,2), how='slice', progressbar=True)
            print(fn)
            cube = DaskSpectralCube.read(fn.replace(".fits", ""), format='casa_image')
            print(cube)
            mxspec = cube.max(axis=(1,2))
            mxspec.write(f'spectra/{fn.replace("{suffix}","max.fits")}',
                         overwrite=True)
            print(time.time() - t0)
