'''
This example uses the WCON JSON-schema to build a DataSource type and then creates a new
DataSource with the values from an instance conforming to the schema
'''


import json
from owmeta_core.context import ClassContext
from owmeta_core import BASE_CONTEXT
from owmeta_core.json_schema import DataSourceTypeCreator
from pkg_resources import Requirement, resource_filename
from rdflib.namespace import Namespace


BASE_SCHEMA_URL = 'http://schema.openworm.org/2020/07/sci/bio/movement'
BASE_DATA_URL = 'http://data.openworm.org/sci/bio/movement'


CONTEXT = ClassContext(imported=(BASE_CONTEXT,),
                      ident=BASE_SCHEMA_URL,
                      base_namespace=BASE_SCHEMA_URL + '#')


_wcon_schema_fname = resource_filename(Requirement.parse('owmeta_core'), 'wcon_schema_2017_06.json')
with open(_wcon_schema_fname, 'r') as f:
    schema = json.load(f)


# The context of the DataSourceTypeCreator determines the definition context for the
# classes created *unless* the schema definitions have an "$id", in which case the value
# of the "$id" field takes precedence
class MovementDataSourceTypeCreator(DataSourceTypeCreator):
    def create_type(self, path, schema):
        self.cdict['base_namespace'] = Namespace(BASE_SCHEMA_URL)
        self.cdict['base_dat_namespace'] = Namespace(BASE_DATA_URL)
        self.cdict['__module__'] = __name__
        return super().create_type(path, schema)


ANNOTATED_SCHEMA = MovementDataSourceTypeCreator('MovementDataSource', context=CONTEXT).annotate(schema)
MovementDataSource = ANNOTATED_SCHEMA
