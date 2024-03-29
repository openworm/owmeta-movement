from setuptools import setup

setup(name='owmeta_movement',
    version='0.0.1',
    install_requires=[
        'owmeta-core>=0.14.0.dev0',
        'owmeta>=0.12.4.dev0',
        'rdflib',
        'pow-store-zodb',
        'requests',
        'beautifulsoup4',
        'cachecontrol[filecache]'],
    extras_require={'plot': ['matplotlib'],
        'tierpsy': ['numpy', 'pandas', 'tables']},
    package_data={'owmeta_movement': ['wcon_schema*.json']},
    packages=['owmeta_movement'],
    entry_points={
        'owmeta_core.commands': [
            'movement = owmeta_movement.command:MovementCommand',
            'zenodo = owmeta_movement.command:ZenodoCommand',
        ],
        'owmeta_core.cli_hints': 'hints = owmeta_movement.cli_hints:CLI_HINTS',
        'owmeta_core.datasource_dir_loader': 'zenodo = owmeta_movement.zenodo:ZenodoRecordDirLoader',
    }
)
