from astroquery.alma import Alma
import os
import shutil
import time
from bs4 import BeautifulSoup

alma = Alma()
rslt = alma.query({'project_code': '2019.1.00092.S'}, public=False)

index = "https://bulk.cv.nrao.edu/almadata/proprietary/keflavich/"
alma.login('keflavich')
ind = alma._request('GET', index, cache=False)
soup = BeautifulSoup(ind.text)
urllist = [index+'/'+xx.attrs['href'].strip("/") for xx in soup.findAll('a')]
['https://bulk.cv.nrao.edu/almadata/proprietary/keflavich/X3a53',
 'https://bulk.cv.nrao.edu/almadata/proprietary/keflavich/X3a5f',
 'https://bulk.cv.nrao.edu/almadata/proprietary/keflavich/X3a57',
 'https://bulk.cv.nrao.edu/almadata/proprietary/keflavich/X3a63',
 'https://bulk.cv.nrao.edu/almadata/proprietary/keflavich/X3a33']

for baseurl in urllist:

    nm = baseurl.split("/")[-1]
    if os.path.exists(f'{nm}_calibrated_final.ms.tgz'):
        print(f"Skipped {baseurl} b/c it's done.")
        continue
    if 'X' not in nm:
        # simply skip...
        continue

    alma = Alma()
    alma.cache_location='.'
    alma.login('keflavich')


    ind = alma._request('GET', baseurl)

    soup = BeautifulSoup(ind.text, parser='lxml')

    urls = [xx.attrs['href'] for xx in soup.findAll('a')]
    urls = [f'{baseurl}/{xx}' for xx in urls if 'gz' in xx]

    print(nm)
    print(urls)

    alma.download_files(urls)

    if os.path.exists('calibrated_final.ms.tgz'):
        if os.path.exists(f'{nm}_calibrated_final.ms.tgz'):
            raise IOError("Already exists!!!!")
        else:
            shutil.move('calibrated_final.ms.tgz', f'{nm}_calibrated_final.ms.tgz')
