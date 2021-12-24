[![Dev Test/Deploy](https://github.com/openworm/owmeta-movement/actions/workflows/dev-test.yml/badge.svg)](https://github.com/openworm/owmeta-movement/actions/workflows/dev-test.yml)
[![Docs](https://readthedocs.org/projects/owmeta-movement/badge/?version=latest)](https://owmeta-movement.readthedocs.io/en/latest)
[![Coverage Status](https://coveralls.io/repos/github/openworm/owmeta-movement/badge.svg?branch=master)](https://coveralls.io/github/openworm/owmeta-movement?branch=master)

owmeta-movement
===============
This repository contains classes and commands for manipulating, displaying, and
sharing *C. elegans* movement data, particularly "tracks" of movement across a
plate as can be expressed with [WCON][WCON].

[WCON]: https://github.com/openworm/tracker-commons/

Install
-------
To get the command line tools (sub-commands to [`owm`][owmeta-cli]) and the
movement data types, you can install with pip:

    pip install owmeta-movement

To ensure support for plotting tracks, install with the `plot`
["extra"][pep508]:

    pip install owmeta-movement[plot]

Likely, you'll also want the owmeta-movement schema bundle for several of the
commands, described further in *Usage* below. To do so, initialize your project
(if you don't already have one):

    owm init --default-context-id "http://example.org/movement"

You can pick whatever you like for the default context ID. Add `{"id":
"openworm/owmeta-movement-schema", "version": 4}` to your `.owm/owm.conf`
file's `dependencies` list. Your `owm.conf` may look something like this:

    {
        "class_registry_context_id": "urn:uuid:33c67b01-a865-4ea3-8407-13b69e22e2d3",
        "default_context_id": "http://example.org/movement",
        "imports_context_id": "urn:uuid:5485296e-83a1-4fad-9518-7106a6a115ee",
        "rdf.source": "zodb",
        "rdf.store_conf": "$OWM/worm.db",
        "rdf.upload_block_statement_count": 50,
        "dependencies": [{"id": "openworm/owmeta-movement-schema", "version": 4}]
    }

Then, you'll need to add a "remote" so `owm` knows where to get the bundle
from:

    owm bundle remote --user add ow 'https://raw.githubusercontent.com/openworm/owmeta-bundles/master/index.json'

Once you have declared a remote with the `--user` option, as show above, you
will not need to declare it again for each new project.

[owmeta-cli]: https://owmeta-core.readthedocs.io/en/latest/command.html
[pep508]: https://www.python.org/dev/peps/pep-0508/#extras

Usage
-----
The OpenWorm *C. elegans* [movement database][OWMD] has several entries, with
various formats. Sub-commands are defined for dealing with some of them. One
entry is from the CeMEE MWT dataset, and we'll describe some commands for
working with it below. Be sure you've followed the instructions for installing
the `openworm/owmeta-movement-schema` bundle above.

First, add a [DataSource][datasource] reference to WCON from the CeMEE MWT
dataset:

    owm movement cemee save 4074963 CeMEE_MWT_founders.tar.gz LSJ2_20190705_105444.wcon.zip --key cemee-mwt-LSJ2_20190705_105444 

This should return the URI for the created DataSource, which, by default, looks
like this:

    http://data.openworm.org/data_sources/ZenodoCeMEEWCONDataSource#cemee-mwt-LSJ2_20190705_105444

but we'll bind a namespace so we don't have to write the whole string in commands:

    owm namespace bind zenodo_cemee 'http://data.openworm.org/data_sources/ZenodoCeMEEWCONDataSource#'


A side effect of this command is *downloading* the referenced file from Zenodo
-- _this is about 550MB for the file in the command above_. However, if the
download completes, running `owm movement cemee save` for the same record and
file should use a version cached in your owmeta project directory, `.owm`.

You can show the attributes of the source you created with this command:

    owm source show 'zenodo_cemee:cemee-mwt-LSJ2_20190705_105444'

You can check out some of the metadata in the downloaded WCON:

    import json

    from owmeta_core.command import OWM
    from owmeta_core.datasource import DataSource

    with OWM().connect() as conn:
        dsq = conn.owm.default_context.stored(DataSource)(
                ident='http://data.openworm.org/data_sources/ZenodoCeMEEWCONDataSource#cemee-mwt-LSJ2_20190705_105444')
        with dsq.load_one().wcon_contents() as f:
            print(json.load(f)['metadata'])

Then you can translate the WCON from the Zenodo record to the `WormTracks`
format, which is essentially a translation of WCON into RDF, which is useful
for commands that operate on this generic format. In addition, because CeMEE
"WCON" does not quite conform to the WCON specification, this will also
translate into a compliant form of WCON. To perform the translation, run these
command:

    owm translator create http://schema.openworm.org/2020/07/CeMEEDataTranslator
    owm movement cemee translate zenodo_cemee:cemee-mwt-LSJ2_20190705_105444

The latter command should return the identifier for the resulting DataSource:

    http://data.openworm.org/sci/data_sources/DataWithEvidenceDataSource#a86e368bfb698cf16647f441a304d6ec9

This is also the identifier of the context that imports the context where
statements in the DataSource are defined. See documentation for
[DataWithEvidenceDataSource][DWEDS] for more information. For convenience,
we'll add that context as an import to the project:

    owm contexts add-import https://example.org/movement http://data.openworm.org/sci/data_sources/DataWithEvidenceDataSource#a86e368bfb698cf16647f441a304d6ec9

You can remove the import later with:

    owm contexts rm-import https://example.org/movement http://data.openworm.org/sci/data_sources/DataWithEvidenceDataSource#a86e368bfb698cf16647f441a304d6ec9

So, finally, for this brief walk-through, you can plot the "WormTracks". First, use
the `list-tracks` sub-command to get the ID:

    owm movement list-tracks

which, for us, yields:

    http://data.openworm.org/sci/bio/movement/WormTracks#aae70bb80b9f6f08528fa08b1e269423f

Then plot it with the `plot` sub-command:

    owm movement plot 'http://data.openworm.org/sci/bio/movement/WormTracks#aae70bb80b9f6f08528fa08b1e269423f'

You can also plot individual tracks in the dataset.

    owm movement plot 'http://data.openworm.org/sci/bio/movement/WormTracks#aae70bb80b9f6f08528fa08b1e269423f' 1

[OWMD]: https://zenodo.org/communities/open-worm-movement-database/
[datasource]: https://owmeta-core.readthedocs.io/en/latest/api/owmeta_core.datasource.html#owmeta_core.datasource.DataSource
[DWEDS]: https://owmeta.readthedocs.io/en/latest/api/owmeta.data_trans.data_with_evidence_ds.html#owmeta.data_trans.data_with_evidence_ds.DataWithEvidenceDataSource


