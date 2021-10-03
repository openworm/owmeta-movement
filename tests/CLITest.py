import pytest
from owmeta_pytest_plugin import bundle_versions


@bundle_versions('movement_bundle', [1])
@pytest.mark.inttest
@pytest.mark.skip
def test_cemee_save(owm_project, movement_bundle):
    # Save CeMEE data
    # Define a WCON datasource
    # Run the translator
    owm_project.sh('owm movement cemee save'
            ' 4074963 CeMEE_MWT_founders.tar.gz LSJ2_20190705_105444.wcon.zip --key=blah')
