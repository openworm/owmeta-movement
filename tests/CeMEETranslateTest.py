import json
import os
from os.path import join as p, isfile
import tempfile

import pytest
from owmeta.evidence import Evidence
from owmeta.document import SourcedFrom, Document
from owmeta_core.context import Context, IMPORTS_CONTEXT_KEY
from owmeta_core.capable_configurable import CAPABILITY_PROVIDERS_KEY
from owmeta_core.capabilities import (FilePathProvider,
                                      OutputFilePathProvider,
                                      CacheDirectoryProvider,
                                      TemporaryDirectoryProvider)

from owmeta_movement import WormTracks
from owmeta_movement.wcon_ds import WCONDataSource
from owmeta_movement.cemee import (CeMEEDataTranslator,
                                   CeMEEWCONDataSource,
                                   CeMEEToWCON202007DataTranslator as _202007DT,
                                   ZenodoCeMEEWCONDataSource)


@pytest.fixture
def context(providers):
    ctx = Context('http://example.com/test-context',
            imported=(WCONDataSource.definition_context,
                CeMEEWCONDataSource.definition_context),
            conf={CAPABILITY_PROVIDERS_KEY: providers,
                IMPORTS_CONTEXT_KEY: 'http://example.org/imports'})
    ctx.mapper.process_classes(WCONDataSource, CeMEEWCONDataSource)
    return ctx


@pytest.fixture
def cemeedt(context):
    return context(CeMEEDataTranslator)()


@pytest.fixture
def cemeewds(context):
    return context(ZenodoCeMEEWCONDataSource)(key='test')


@pytest.fixture
def cemeewdsf(context):
    def f(**kwargs):
        return context(ZenodoCeMEEWCONDataSource)(key='test', **kwargs)
    return f


def test_translate_missing_sample_zip_file_name(context, cemeedt, cemeewdsf):
    source = cemeewdsf(zenodo_id=1010101,
            zenodo_file_name='zenodo_fname')
    with pytest.raises(Exception, match='sample_zip_file_name'):
        cemeedt(source)


def test_translate_sample_zip_file_name_wrong_ext(context, cemeedt, cemeewdsf):
    source = cemeewdsf(zenodo_id=1010101,
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='blah.txt')
    with pytest.raises(Exception, match='sample_zip_file_name.*zip'):
        cemeedt(source)


def test_translate_missing_file(context, cemeedt, cemeewdsf):
    source = cemeewdsf(zenodo_id=1010101,
            file_name='zenodo_fname',
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='blah.zip')
    with pytest.raises(Exception, match='zenodo_fname'):
        cemeedt(source)


def test_translate_zip_not_found(context, cemeedt, cemeewdsf):
    source = cemeewdsf(zenodo_id=1010101,
            file_name='test_cemee_file.tar.gz',
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='blah.zip')
    with pytest.raises(Exception, match='blah.zip'):
        cemeedt(source)


@pytest.fixture
def cemeedt_result(context, cemeedt, cemeewdsf):
    source = cemeewdsf(zenodo_id=1010101,
            file_name='test_cemee_file.tar.gz',
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='LSJ2_20190705_105444.wcon.zip')
    return cemeedt(source, output_key='test')


def test_translate_result_has_tracks(cemeedt_result):
    tracks = cemeedt_result.data_context(WormTracks)()
    tracksets = list(tracks.load())
    assert len(tracksets) == 1


def test_translate_result_no_evidence(cemeedt_result):
    '''
    We do not attach any documents to the result unless they are present on the source
    '''
    ev = cemeedt_result.evidence_context(Evidence)()
    assert len(list(ev.load())) == 0


def test_translators_delete_tempdirs(cemeedt, cemeedt_result, tmp_path):
    assert not any([d.startswith('_TempDirProvider') for d in os.listdir(tmp_path)])


@pytest.fixture
def cemee_translation_res(providers):
    conf = {CAPABILITY_PROVIDERS_KEY: providers}
    ctx = Context('http://example.org/ctx',
            conf=conf,
            imported=(WCONDataSource.definition_context,))
    ctx.mapper.process_class(WCONDataSource)
    cut = ctx(_202007DT)(conf=conf)
    source = ctx(CeMEEWCONDataSource)(key='1010101',
            file_name='test_cemee_file.tar.gz',
            sample_zip_file_name='LSJ2_20190705_105444.wcon.zip',
            conf=conf)
    out = cut(source, output_identifier='http://example.org/result_wcon')
    for m in out.load():
        return m
    else:
        raise Exception('Could not load result data source')


def test_translate_lab(cemee_translation_res):
    with open(cemee_translation_res.full_path()) as f:
        wcon = json.load(f)
        assert wcon['metadata']['lab']['name'] == 'EEV'


def test_data_list(cemee_translation_res):
    '''
    Test that the data list is actually list and not a dict
    '''
    with open(cemee_translation_res.full_path()) as f:
        wcon = json.load(f)
        assert wcon['data'][0]['id'] == '6'


def test_cemeedt_with_evidence(context, cemeedt, cemeewdsf):
    source = cemeewdsf(
            file_name='test_cemee_file.tar.gz',
            zenodo_file_name='zenodo_fname',
            sample_zip_file_name='LSJ2_20190705_105444.wcon.zip')
    doc = context(Document)(key='cemeeMWT2020', doi='10.5281/zenodo.4074963')
    source.attach_property(SourcedFrom)(doc)
    dweds_res = cemeedt(source, output_key='test')
    ref = dweds_res.evidence_context(Evidence)().reference()
    assert ref.identifier == doc.identifier


# TODO: Test with zip file already cached.


@pytest.fixture
def providers(tmp_path):
    fp_prov = _CeMEEFileProvider()
    cache_prov = _CacheProvider(tmp_path)
    tempdir_prov = _TempDirProvider(tmp_path)
    outdir_prov = _OutFileProvider(tmp_path)
    wconfile_prov = _WCONFileProvider(tmp_path)
    return fp_prov, cache_prov, tempdir_prov, outdir_prov, wconfile_prov


class _CeMEEFileProvider(FilePathProvider):
    def provides_to(self, ob, cap):
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

    def provides_to(self, ob, cap):
        return self


class _TempDirProvider(TemporaryDirectoryProvider):
    def __init__(self, base):
        self.base = base

    def temporary_directory(self):
        return tempfile.mkdtemp(prefix='_TempDirProvider.', dir=self.base)

    def provides_to(self, ob, cap):
        return self


class _WCONFileProvider(FilePathProvider):
    def __init__(self, base):
        self.base = base
        self.dir = p(self.base, 'output')

    def provides_to(self, ob, cap):
        if (isinstance(ob, WCONDataSource) and
                ob.file_name.one() and
                isfile(p(self.dir, ob.file_name.one()))):
            return self
        return None

    def file_path(self):
        return self.dir


class _OutFileProvider(OutputFilePathProvider):
    def __init__(self, base):
        self.base = base
        self.dir = p(self.base, 'output')
        os.mkdir(self.dir)

    def provides_to(self, ob, cap):
        if isinstance(ob, WCONDataSource):
            return self
        return None

    def output_file_path(self):
        return self.dir
