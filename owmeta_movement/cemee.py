from os import makedirs
from os.path import splitext, join as p, isfile
import io
import json
import shutil
import tarfile
import tempfile
import zipfile
from contextlib import contextmanager

from owmeta.data_trans.data_with_evidence_ds import DataWithEvidenceDataSource
from owmeta.evidence import Evidence
from owmeta_core.utils import FCN
from owmeta_core.capability import NoProviderGiven
from owmeta_core.capabilities import (FilePathCapability,
                                      CacheDirectoryCapability,
                                      TemporaryDirectoryCapability)
from owmeta_core.capable_configurable import CapableConfigurable
from owmeta_core.data_trans.local_file_ds import CommitOp
from owmeta_core.datasource import DataTranslator, Informational
from owmeta_core.json_schema import DataObjectCreator
from owmeta_core.collections import Seq

from . import WormTracks, CONTEXT, DataLiteral, WCON_SCHEMA_2020_07
from .wcon_ds import WCONDataSource
from .zenodo import ZenodoFileDataSource, ZenodoRecord


class CeMEEWCONDataSource(ZenodoFileDataSource):
    '''
    A DataSource providing WCON from the CeMEE MWT dataset on Zenodo
    '''
    class_context = CONTEXT
    needed_capabilities = [FilePathCapability(), CacheDirectoryCapability()]

    sample_zip_file_name = Informational(description='Name of the WCON zip within the'
            ' archive file from the Zenodo record. Nominally, corresponds to a sample'
            ' identified by its strain and a timestamp', multiple=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not hasattr(self, '_cache_provider'):
            self._cache_provider = None

    def accept_capability_provider(self, cap, provider):
        if isinstance(cap, CacheDirectoryCapability):
            self._cache_provider = provider
        else:
            super().accept_capability_provider(cap, provider)

    @contextmanager
    def wcon_contents(self):
        '''
        Return the wcon file contents
        '''
        # TODO: Make this return a properly formatted WCON file
        zenodo_id = self.zenodo_id.one()
        if not zenodo_id:
            raise Exception('Missing `zenodo_id`')

        zenodo_file_name = self.zenodo_file_name.one()
        if not zenodo_file_name:
            raise Exception('Missing `zenodo_file_name`')

        sample_zip_file_name = self.sample_zip_file_name.one()
        if not sample_zip_file_name:
            raise Exception('Missing `sample_zip_file_name`')

        sample_wcon_file_name, ext = splitext(sample_zip_file_name)

        if ext != '.zip':
            raise Exception('Expected sample_zip_file_name to be a zip file name')

        cache_directory = None
        if self._cache_provider:
            cache_directory = self._cache_provider.cache_directory(FCN(type(self)))

        cleanup_dir = False
        if cache_directory is None:
            cache_directory = tempfile.mkdtemp()
            cleanup_dir = True
        mycachedir = p(cache_directory, str(zenodo_id))
        makedirs(mycachedir, exist_ok=True)

        try:
            # May re-evaluate this for resilience -- as it is, we could fail part-way
            # through and have to redo everything
            cached_tar_file_name = self.full_path()

            wcon_zip_file_name = p(mycachedir, sample_zip_file_name)
            if isfile(wcon_zip_file_name):
                # TODO: check the file is the one we expect
                pass
            else:
                with tarfile.open(cached_tar_file_name) as tf:
                    tf.extract(sample_zip_file_name, mycachedir)

            with zipfile.ZipFile(wcon_zip_file_name) as zf, \
                    zf.open(sample_wcon_file_name) as wcon:
                yield wcon
        finally:
            if cleanup_dir:
                shutil.rmtree(cache_directory)


class CeMEEToWCON202007DataTranslator(CapableConfigurable, DataTranslator):
    '''
    Corrects the pseudo-WCON format into a form compliant with the 2020/07 version of the
    WCON Schema
    '''

    needed_capabilities = [TemporaryDirectoryCapability()]

    input_types = (CeMEEWCONDataSource,)
    output_type = WCONDataSource

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, '_tempdir'):
            self._tempdir = None

    def accept_capability_provider(self, cap, provider):
        if isinstance(cap, TemporaryDirectoryCapability):
            self._tempdir = provider.temporary_directory()
        else:
            super().accept_capability_provider(cap, provider)

    def translate(self, source):

        dest = self.make_new_output((source,))
        if self._tempdir is None:
            raise NoProviderGiven(TemporaryDirectoryCapability())
        with source.wcon_contents() as wcon:
            wcon_json = json.load(wcon)
            # CeMEE wants to be special... fix up their data
            try:
                lab = wcon_json['metadata']['lab']
                if isinstance(lab, str):
                    wcon_json['metadata']['lab'] = {'name': lab}
            except KeyError:
                pass

            try:
                software = wcon_json['units']['software']
                del wcon_json['units']['software']
                wcon_json.setdefault('metadata', {})['software'] = software
            except KeyError:
                pass

            try:
                food = wcon_json['units']['food']
                del wcon_json['units']['food']
                wcon_json.setdefault('metadata', {})['food'] = food
            except KeyError:
                pass
            data = wcon_json['data']
            if isinstance(data, dict) and 'x' not in data:
                # 'x' is required in a data record, so this was *probably* supposed to
                # be an array, so let's pretend it is one
                new_data = dict()
                for index, record in data.items():
                    # CeMEE uses integers for the IDs, but we need strings
                    record['id'] = str(record['id'])
                    # Fix the dimensions of the data: each field is a singleton list, but
                    # they should all be lists of numbers
                    record['t'] = record['t'][0]
                    record['x'] = record['x'][0]
                    record['y'] = record['y'][0]
                    for extra_field, extra_val in record['@MWT'].items():
                        record['@MWT'][extra_field] = extra_val[0]
                    new_data[int(index)] = record
                wcon_json['data'] = _SparseList(new_data)
            sample_wcon_file_name, _ = splitext(source.sample_zip_file_name.one())
            dest.file_name(sample_wcon_file_name)
            dest.source_file_path = p(self._tempdir, sample_wcon_file_name)

            dest.commit_op = CommitOp.RENAME
            with open(dest.source_file_path, 'w') as outfile:
                json.dump(wcon_json, outfile)
            return dest


class CeMEEDataTranslator(DataTranslator):
    '''
    Dealing with the CeMEE Multi-Worm Tracker entries.

    See https://zenodo.org/record/4074963 for more.
    '''
    class_context = CONTEXT
    input_types = (CeMEEWCONDataSource,)
    output_type = DataWithEvidenceDataSource

    def translate(self, source):
        with source.wcon_contents() as wcon:
            wcon_json = json.load(wcon)
            # CeMEE wants to be special... fix up their data
            try:
                lab = wcon_json['metadata']['lab']
                if isinstance(lab, str):
                    wcon_json['metadata']['lab'] = {'name': lab}
            except KeyError:
                pass

            try:
                software = wcon_json['units']['software']
                del wcon_json['units']['software']
                wcon_json.setdefault('metadata', {})['software'] = software
            except KeyError:
                pass

            try:
                food = wcon_json['units']['food']
                del wcon_json['units']['food']
                wcon_json.setdefault('metadata', {})['food'] = food
            except KeyError:
                pass
            data = wcon_json['data']
            if isinstance(data, dict) and 'x' not in data:
                # 'x' is required in a data record, so this was *probably* supposed to
                # be an array, so let's pretend it is one
                new_data = dict()
                for index, record in data.items():
                    # CeMEE uses integers for the IDs, but we need strings
                    record['id'] = str(record['id'])
                    # Fix the dimensions of the data: each field is a singleton list, but
                    # they should all be lists of numbers
                    record['t'] = record['t'][0]
                    record['x'] = record['x'][0]
                    record['y'] = record['y'][0]
                    for extra_field, extra_val in record['@MWT'].items():
                        record['@MWT'][extra_field] = extra_val[0]
                    new_data[int(index)] = record
                wcon_json['data'] = _SparseList(new_data)
            res = self.make_new_output((source,))

            res.data_context.add_import(WormTracks.definition_context)
            res.evidence_context.add_import(Evidence.definition_context)
            res.evidence_context.add_import(ZenodoRecord.definition_context)

            tracks = res.data_context(WormTracks)(key=res.identifier, direct_key=False)
            zenodo_id = source.zenodo_id.one()
            record = res.evidence_context(ZenodoRecord)(zenodo_id=zenodo_id)
            res.evidence_context(Evidence)(
                    reference=record,
                    supports=res.data_context)
            CeMEEDataSourceCreator(WCON_SCHEMA_2020_07).fill_in(tracks, wcon_json,
                    context=res.data_context)
            return res


class CeMEEDataSourceCreator(DataObjectCreator):
    '''
    Creates WormTracks from CeMEE Zenodo records
    '''
    # XXX: This class might end up being a WCONDataObjectCreator instead... we massage the
    # WCON into the right format in the DataTranslator for each type, but the mapping from
    # well-formed WCON to WormTracks can be shared.
    def begin_sequence(self, schema):
        path = self.path_stack
        if len(path) == 1 and path[0] == 'data':
            return Seq.contextualize(self.context)(ident=self.gen_ident())
        return super().begin_sequence(schema)

    def add_to_sequence(self, schema, sequence, idx, item):
        path = self.path_stack
        if isinstance(sequence, Seq) and len(path) == 2 and path[0] == 'data':
            if item is None:
                return sequence
            sequence[idx] = item
            return sequence
        return super().add_to_sequence(schema, sequence, idx, item)

    def assign(self, obj, key, val):
        path = self.path_stack
        if len(path) == 2 and path[0] == 'data' and isinstance(val, (dict, list)):
            val = DataLiteral(val)
        super().assign(obj, key, val)


_NOPE = object()


class _SparseList(list):
    def __init__(self, base):
        self._base = base

    def __getitem__(self, index):
        try:
            self._base[index]
        except KeyError:
            raise IndexError(index)

    def __setitem__(self, index, value):
        self._base[index] = value

    def __iter__(self):
        index = 0
        maxhits = len(self._base)
        hits = 0
        while True:
            item = self._base.get(index, _NOPE)
            if item is not _NOPE:
                hits += 1
            else:
                item = None
            yield item
            index += 1
            if hits >= maxhits:
                break

    def __str__(self):
        res = io.StringIO()
        res.write('[')
        keys = sorted(self._base.keys())
        last = -1
        first = True
        for m in keys:
            if m - last > 1:
                if not first:
                    res.write(',')
                res.write(' ')
            if m > 0:
                res.write(', ')
            res.write(str(self._base[m]))
            first = False
            last = m
        res.write(']')
        return res.getvalue()

    def __repr__(self):
        return f'_SparseList({self._base})'
