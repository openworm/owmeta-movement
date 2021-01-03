from setuptools import setup

setup(name='owmeta_movement',
      install_requires=[
          'owmeta-core',
          'rdflib',
          'pow-store-zodb',
          'requests',
          'cachecontrol[filecache]'],
      extras_require={'plot': ['matplotlib']},
      package_data={'owmeta_movement': ['wcon_schema*.json']},
      packages=['owmeta_movement'])
