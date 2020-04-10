import glob
import pyspeckit
import pylab as pl

fig=pl.figure(figsize=(25,10))

spectra = pyspeckit.Spectra(pyspeckit.Spectrum(x) for x in glob.glob("spectra/*max.fits"))
spectra.plotter(figure=fig)

spectra.plotter.figure.savefig('full_spectrum_max.png', dpi=200, bbox_inches='tight')
