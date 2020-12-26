'''
This example uses the WCON JSON-schema to build a DataSource type and then creates a new
DataSource with the values from an instance conforming to the schema
'''
import json
import importlib
from owmeta_core.context import ClassContext
from owmeta_core import BASE_CONTEXT
from owmeta_core.json_schema import DataSourceTypeCreator
from pkg_resources import resource_stream
from rdflib.namespace import Namespace


BASE_SCHEMA_URL = 'http://schema.openworm.org/2020/07/sci/bio/movement'
BASE_DATA_URL = 'http://data.openworm.org/sci/bio/movement'


CONTEXT = ClassContext(imported=(BASE_CONTEXT,),
                      ident=BASE_SCHEMA_URL,
                      base_namespace=BASE_SCHEMA_URL + '#')


class MovementDataSourceTypeCreator(DataSourceTypeCreator):

    def __init__(self, schema, **kwargs):
        super().__init__('MovementDataSource', schema,
                module=__name__,
                context=CONTEXT,
                **kwargs)

    def create_type(self, path, schema):
        cdict = self.cdict.setdefault(path, {})
        cdict['base_namespace'] = Namespace(BASE_SCHEMA_URL + '/')
        cdict['base_data_namespace'] = Namespace(BASE_DATA_URL + '/')
        res = super().create_type(path, schema)
        mod = importlib.import_module(__name__)
        setattr(mod, res.__name__, res)
        res.register_on_module(mod)
        return res


_wcon_schema = resource_stream('owmeta_movement', 'wcon_schema_2017_06.json')
with _wcon_schema:
    _schema = json.load(_wcon_schema)
ANNOTATED_SCHEMA = MovementDataSourceTypeCreator(_schema).annotate()
