import glob
import pyspeckit

spectra = pyspeckit.Spectra(pyspeckit.Spectrum(x) for x in glob.glob("spectra/*max.fits"))
spectra.plotter()

spectra.plotter.figure.savefig('full_spectrum_max.png')
