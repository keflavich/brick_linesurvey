from astroquery.alma import Alma
import time

alma = Alma()
rslt = alma.query({'project_code': '2019.1.00092.S'}, public=False, cache=False)
print(rslt['Member ous id','QA2 Status'])

#for mousid in rslt['Member ous id'][:-1]:
for mousid in ['uid://A001/X1465/X3a53']:
    print(mousid)
    alma = Alma()
    alma.cache_location='.'
    alma.login('keflavich')
    try:
        stage = alma.stage_data(mousid)
    except:
        print(f"Staging mousid {mousid} failed")
    try:
        alma.download_files(stage['URL'])
    except Exception as ex:
        print(ex)
        try:
            print(f"trying w/API")
            apifiles = [x.replace("dataPortal","dataPortal/api")
                        for x in stage['URL']]
            print(apifiles)
            alma.download_files(apifiles, savedir='.',
                                cache=True, continuation=True,
                                skip_unauthorized=False)
        except Exception as ex:
            raise(ex)
            print(ex)
            for try_number in range(5):
                try:
                    print(f"trying w/sso: try number {try_number}")
                    alma.download_files([x.replace("dataPortal","dataPortal/sso")
                                         for x in stage['URL']], savedir='.',
                                        cache=True, continuation=True)
                    break
                except Exception as ex:
                    print(ex)
                time.sleep(1)
        print()
