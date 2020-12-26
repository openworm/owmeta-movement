from owmeta_core.dataobject import ClassDescription
from owmeta_core.data import Data
from owmeta_core.context import Context
from owmeta_movement import MovementDataSource


def test_make_MovementDataSource_module():
    assert MovementDataSource.__module__ == 'owmeta_movement'


def test_load_from_class_description():
    '''
    Test that we can load from a MDS description
    '''
    dat = Data()
    dat['imports_context_id'] = 'http://example.org/imports'
    dat.init()

    crctxid = 'http://example.org/class_registry'
    crctx = Context(crctxid, conf=dat)
    crctx.add_import(ClassDescription.definition_context)
    cd = crctx(MovementDataSource).declare_class_description()
    crctx.save()
    crctx.save_imports()
    ClassDescription.definition_context.save(dat['rdf.graph'])

    print(dat['rdf.graph'].serialize(format='n3').decode('UTF-8'))
    qcrctx = Context(crctxid, conf=dat).stored
    for rcd in qcrctx(ClassDescription)(ident=cd.identifier).load():
        assert 'MovementDataSource' == rcd.resolve_class().__name__
        break
    else: # no break
        assert False, 'Should have gotten a class description'
