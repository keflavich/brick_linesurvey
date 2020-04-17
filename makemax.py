import os
import glob
from spectral_cube import SpectralCube
from spectral_cube.dask_spectral_cube import DaskSpectralCube

import time

dask = True

if dask:
    from dask.diagnostics import ProgressBar
    pbar = ProgressBar()
    pbar.register()

for suffix in ("image.pbcor.fits",):
    for fn in glob.glob(f"BrickMaser*{suffix}"):
        t0 = time.time()
        outf_ = fn.replace(suffix,"max.fits")
        outfn = f'spectra/{outf_}'
        print(fn, outfn)
        if not os.path.exists(outfn):
            if not dask:
                cube = SpectralCube.read(fn)
                print(cube)
                mxspec = cube.max(axis=(1,2), how='slice', progressbar=True)
            else:
                print(fn)
                cube = DaskSpectralCube.read(fn.replace(".fits", ""), format='casa_image')
                print(cube)
                mxspec = cube.max(axis=(1,2))

            mxspec.write(outfn,
                         overwrite=True)
            print(time.time() - t0)
