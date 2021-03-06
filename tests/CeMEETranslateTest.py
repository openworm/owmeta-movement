import os
from os.path import join as p, exists
import tempfile

import pytest
from owmeta.evidence import Evidence
from owmeta_core.capability import provide
from owmeta_core.capable_configurable import CAPABILITY_PROVIDERS_KEY
from owmeta_core.capabilities import (FilePathProvider,
                                      CacheDirectoryProvider,
                                      TemporaryDirectoryProvider)

from owmeta_movement import WormTracks
from owmeta_movement.wcon_ds import WCONDataSource
from owmeta_movement.cemee import (CeMEEDataTranslator,
                                   CeMEEWCONDataSource,
                                   CeMEEToWCON202007DataTranslator as _202007DT)


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


def test_translate_result_has_tracks(providers):
    source = CeMEEWCONDataSource(zenodo_id=1010101,
            file_name='test_cemee_file.tar.gz',
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='LSJ2_20190705_105444.wcon.zip')
    provide(source, providers)
    cut = CeMEEDataTranslator()
    dweds = cut(source, output_key='test')
    tracks = dweds.data_context(WormTracks)()
    tracksets = list(tracks.load())
    assert len(tracksets) == 1


def test_translate_result_evidence(providers):
    source = CeMEEWCONDataSource(zenodo_id=1010101,
            file_name='test_cemee_file.tar.gz',
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='LSJ2_20190705_105444.wcon.zip')
    provide(source, providers)
    cut = CeMEEDataTranslator()
    dweds = cut(source, output_key='test')
    ev = dweds.evidence_context(Evidence)()
    assert len(list(ev.load())) == 1


def test_translate_lab(providers):
    conf = {CAPABILITY_PROVIDERS_KEY: providers}
    cut = _202007DT(conf=conf)
    source = CeMEEWCONDataSource(zenodo_id=1010101,
            file_name='test_cemee_file.tar.gz',
            zenodo_file_name='test_cemee_file.tar.gz',
            sample_zip_file_name='LSJ2_20190705_105444.wcon.zip',
            conf=conf)
    out = cut(source)
    out.commit()


# TODO: Test with zip file already cached.


@pytest.fixture
def providers(tmp_path):
    fp_prov = _CeMEEFileProvider()
    cache_prov = _CacheProvider(tmp_path)
    tempdir_prov = _TempDirProvider(tmp_path)
    outdir_prov = _OutFileProvider(tmp_path)
    return fp_prov, cache_prov, tempdir_prov, outdir_prov


class _CeMEEFileProvider(FilePathProvider):
    def provides_to(self, ob):
        if isinstance(ob, CeMEEWCONDataSource):
            return self
        return None

    def file_path(self):
        return p('tests', 'testdata')


class _CacheProvider(CacheDirectoryProvider):
    def __init__(self, base):
        self.base = base

    def clear(self, cache_key):
        pass

    def cache_directory(self, cache_key):
        return p(self.base, 'cache')

    def provides_to(self, ob):
        return self


class _TempDirProvider(TemporaryDirectoryProvider):
    def __init__(self, base):
        self.base = base

    def temporary_directory(self):
        return tempfile.mkdtemp(dir=self.base)

    def provides_to(self, ob):
        return self


class _OutFileProvider(FilePathProvider):
    def __init__(self, base):
        self.base = base

    def provides_to(self, ob):
        if isinstance(ob, WCONDataSource):
            return self
        return None

    def file_path(self):
        res = p(self.base, 'output')
        os.mkdir(res)
        return res
