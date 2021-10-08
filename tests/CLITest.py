import json
import os.path as OP

import pytest
from owmeta_pytest_plugin import bundle_versions


@pytest.fixture
def cemee_record_info():
    with open(OP.join('tests', 'testdata', 'cemeemwt_record_info.json')) as f:
        return json.load(f)


@bundle_versions('movement_bundle', [1])
@pytest.mark.inttest
def test_cemee_save(owm_project, movement_bundle, cemee_record_info):
    # Save CeMEE data
    # Define a WCON datasource
    # Run the translator
    owm_project.sh(('owm movement cemee save'
            ' {record_id} {file_name} {zip_file_name}'
            ' --zenodo-base-url={base_url} --key=blah').format(**cemee_record_info))
