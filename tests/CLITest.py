import pytest
from owmeta_pytest_plugin import bundle_versions


@bundle_versions('movement_bundle', [1])
@pytest.mark.inttest
def test_cemee_save(owm_project, movement_bundle):
    # Save CeMEE data
    # Define a WCON datasource
    # Run the translator
    owm_project.sh('owm movement cemee save 12345 blah_fname blah_zipfile --key=blah')
