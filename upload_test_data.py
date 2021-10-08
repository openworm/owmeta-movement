import json
from os.path import join as pth_join
from os import environ

import requests


ACCESS_TOKEN = environ['ZENODO_ACCESS_TOKEN']
headers = {"Content-Type": "application/json"}
params = {'access_token': ACCESS_TOKEN}
deposition_data = dict(metadata=dict(
    upload_type='dataset',
    title='CeMEE MWT test dataset',
    creators=[dict(name='Mark Watts', affiliation='OpenWorm')],
    description=('A dataset for testing owmeta-movement integration with'
                 ' Zenodo for CeMEEMWT data'),
    access_right='open',
    license='cc-nc',
))

# deposition_data={}
r = requests.post('https://sandbox.zenodo.org/api/deposit/depositions',
               params=params,
               json=deposition_data,
               # Headers are not necessary here since "requests" automatically
               # adds "Content-Type: application/json", because we're using
               # the "json=" keyword argument
               # headers=headers,
               headers=headers)

if r.status_code != 201:
    raise Exception('Failed to create zenodo record.'
            f' Received status code {r.status_code}. Response: {r.text}')
deposit_resp = r.json()
bucket_url = deposit_resp['links']['bucket']
publish_url = deposit_resp['links']['publish']
deposition_url = deposit_resp['links']['self']
record_id = deposit_resp['record_id']
print(f"Record ID: {record_id}")

file_name = 'test_cemee_file.tar.gz'
src = pth_join('tests', 'testdata', file_name)
with open(src, "rb") as fp:
    r = requests.put(
        "%s/%s" % (bucket_url, file_name),
        data=fp,
        params=params,
    )

if r.status_code != 200:
    raise Exception(f'Failed to upload file to zenodo record for {deposition_url}')
print(f"File upload response: {r.text}")
r = requests.post(publish_url, params=params)

if r.status_code not in (200, 202):
    raise Exception(f'Failed to publish. Received status code: {r.status_code}')

with open(pth_join('tests', 'testdata', 'cemeemwt_record_info.json'), 'w') as f:
    json.dump(dict(
        record_id=str(record_id),
        file_name='test_cemee_file.tar.gz',
        zip_file_name='LSJ2_20190705_105444.wcon.zip'), f)
