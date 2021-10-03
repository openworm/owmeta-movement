import json

from owmeta_core.datasource import DataTranslator
from owmeta_core.data_trans.local_file_ds import LocalFileDataSource
from owmeta.data_trans.data_with_evidence_ds import DataWithEvidenceDataSource
from owmeta.document import SourcedFrom
from owmeta.evidence import Evidence

from . import WormTracks, CONTEXT, WCONWormTracksCreator_2020_07


class WCONDataSource(LocalFileDataSource):
    '''
    A `LocalFileDataSource` for a *valid* WCON file
    '''
    class_context = CONTEXT
    # This is just a marker at this point


class WCONDataTranslator(DataTranslator):
    '''
    Takes valid WCON data and turns it into WormTracks
    '''
    class_context = CONTEXT
    input_types = (WCONDataSource,)
    output_type = DataWithEvidenceDataSource

    def translate(self, source):
        with source.file_contents() as wcon:
            wcon_json = json.load(wcon)
            res = self.make_new_output((source,))

            res.data_context.add_import(WormTracks.definition_context)

            source_documents = source.attach_property(SourcedFrom).get()
            if source_documents:
                res.evidence_context.add_import(Evidence.definition_context)
            for source_document in source_documents:
                res.evidence_context(Evidence)(
                        reference=source_document,
                        supports=res.data_context)

            tracks = res.data_context(WormTracks)(key=res.identifier, direct_key=False)
            WCONWormTracksCreator_2020_07.fill_in(tracks, wcon_json,
                    context=res.data_context)
            return res
