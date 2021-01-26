from os.path import join as p

import pytest
from owmeta_core.capability import provide
from owmeta_core.capabilities import FilePathProvider, CacheDirectoryProvider

from owmeta_movement import MovementDataSource
from owmeta_movement.cemee import CeMEEDataTranslator, CeMEEWCONDataSource


def test_translate_missing_zenodo_id(providers):
    source = CeMEEWCONDataSource()
    provide(source, providers)
    cut = CeMEEDataTranslator()
    with pytest.raises(Exception, match='zenodo_id'):
        cut.translate(source)


def test_translate_missing_zenodo_file_name(providers):
    source = CeMEEWCONDataSource(zenodo_id=1010101)
    provide(source, providers)
    cut = CeMEEDataTranslator()
    with pytest.raises(Exception, match='zenodo_file_name'):
        cut.translate(source)


def test_translate_missing_sample_zip_file_name(providers):
    source = CeMEEWCONDataSource(zenodo_id=1010101,
            zenodo_file_name='zenodo_fname')
    provide(source, providers)
    cut = CeMEEDataTranslator()
    with pytest.raises(Exception, match='sample_zip_file_name'):
        cut.translate(source)


def test_translate_sample_zip_file_name_wrong_ext(providers):
    source = CeMEEWCONDataSource(zenodo_id=1010101,
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='blah.txt')
    provide(source, providers)
    cut = CeMEEDataTranslator()
    with pytest.raises(Exception, match='sample_zip_file_name.*zip'):
        cut.translate(source)


def test_translate_missing_file(providers):
    source = CeMEEWCONDataSource(zenodo_id=1010101,
            file_name='zenodo_fname',
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='blah.zip')
    provide(source, providers)
    cut = CeMEEDataTranslator()
    with pytest.raises(Exception, match='zenodo_fname'):
        cut.translate(source)


def test_translate_zip_not_found(providers):
    source = CeMEEWCONDataSource(zenodo_id=1010101,
            file_name='test_cemee_file.tar.gz',
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='blah.zip')
    provide(source, providers)
    cut = CeMEEDataTranslator()
    with pytest.raises(Exception, match='blah.zip'):
        cut.translate(source)


def test_translate_result_has_movement_data(providers):
    source = CeMEEWCONDataSource(zenodo_id=1010101,
            file_name='test_cemee_file.tar.gz',
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='LSJ2_20190705_105444.wcon.zip')
    provide(source, providers)
    cut = CeMEEDataTranslator()
    dweds = cut(source, output_key='test')
    mds = dweds.data_context(MovementDataSource)()
    assert len(list(mds.load())) > 0

# TODO: Test with zip file already cached.


@pytest.fixture
def providers(tmp_path):
    fp_prov = _CeMEEFileProvider()
    cache_prov = _CacheProvider(tmp_path)
    return fp_prov, cache_prov


class _CeMEEFileProvider(FilePathProvider):
    def provides_to(self, ob):
        return self

    def file_path(self):
        return p('tests', 'testdata')


class _CacheProvider(CacheDirectoryProvider):
    def __init__(self, base):
        self.base = base

    def clear(self):
        pass

    def cache_directory(self):
        return p(self.base, 'cache')

    def provides_to(self, ob):
        return self
