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
from owmeta_core.capabilities import FilePathCapability, CacheDirectoryCapability
from owmeta_core.datasource import DataTranslator, Informational
from owmeta_core.json_schema import DataObjectCreator
from owmeta_core.collections import Seq

from . import MovementDataSource, CONTEXT, DataLiteral, WCON_SCHEMA_2020_07
from .zenodo import ZenodoFileDataSource


class CeMEEWCONDataSource(ZenodoFileDataSource):
    class_context = CONTEXT
    needed_capabilities = [FilePathCapability(), CacheDirectoryCapability()]

    sample_zip_file_name = Informational(description='Name of the WCON zip within the'
            ' archive file from the Zenodo record. Nominally, corresponds to a sample'
            ' identified by its strain and a timestamp', multiple=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
            cache_directory = self._cache_provider.cache_directory()

        cleanup_dir = False
        if cache_directory is None:
            cache_directory = tempfile.mkdtemp()
            cleanup_dir = True
        mycachedir = p(cache_directory, str(zenodo_id))
        makedirs(mycachedir, exist_ok=True)

        try:
            # May re-evaluate this for resilence -- as it is, we could fail part-way
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


class CeMEEDataTranslator(DataTranslator):
    '''
    Dealing with the CeMEE Multi-Worm Tracker entries.

    See https://zenodo.org/record/4074963 for more.
    '''
    input_types = (CeMEEWCONDataSource,)
    output_type = DataWithEvidenceDataSource

    def translate(self, source):
        # Assign these to self just to avoid the
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
                    # The times don't match
                    record['t'] = record['t'][0]
                    new_data[int(index)] = record
                wcon_json['data'] = _SparseList(new_data)
            res = self.make_new_output((source,))
            mds = res.data_context(MovementDataSource)(key=res.identifier)
            # TODO: Create evidence and put it in the evidence context.
            CeMEEDataSourceCreator(WCON_SCHEMA_2020_07).fill_in(mds, wcon_json,
                    context=res.data_context)
            return res


class CeMEEDataSourceCreator(DataObjectCreator):
    '''
    Creates MovementDataSources from CeMEE Zenodo records
    '''
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
