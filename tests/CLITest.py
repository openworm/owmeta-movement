import json
import os.path as OP

import pytest
from owmeta_core.datasource import DataSource
from owmeta_pytest_plugin import bundle_versions
from owmeta_movement.cemee import CeMEEDataTranslator
from owmeta_movement import WormTracks


@pytest.fixture
def cemee_record_info():
    with open(OP.join('tests', 'testdata', 'cemeemwt_record_info.json')) as f:
        return json.load(f)


@bundle_versions('movement_bundle', [3])
@pytest.mark.bundle_remote('ow')
@pytest.mark.inttest
def test_cemee_save(owm_project, movement_bundle, cemee_record_info):
    # Save CeMEE data
    # Define a WCON datasource
    # Run the translator
    owm_project.fetch(movement_bundle)
    deps = [{"id": movement_bundle.id, "version": movement_bundle.version}]
    deps_json = json.dumps(deps)
    owm_project.sh(f'owm config set dependencies \'{deps_json}\'')
    owm_project.sh(
            f'owm translator create {CeMEEDataTranslator.rdf_type}').strip()
    source_id = owm_project.sh(('owm movement cemee save'
            ' {record_id} {file_name} {zip_file_name}'
            ' --zenodo-base-url={base_url}'
            ' --key=blah').format(**cemee_record_info)).strip()
    output = owm_project.sh(f'owm movement cemee translate {source_id}')
    owm = owm_project.owm()
    with owm.connect():
        print("default context", owm.default_context)
        for dweds in owm.default_context.stored(DataSource)(ident=output).load():
            print("dweds", dweds)
            for tracks in dweds.data_context(WormTracks)().load():
                print("tracks", tracks)
                data = tracks.data().one()
                print("data", data)
                assert data[0].id() == '6'
