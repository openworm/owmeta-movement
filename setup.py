from setuptools import setup

setup(name='owmeta_movement',
      install_requires=[
          'owmeta_core',
          'sickle'],
      package_data={'owmeta_movement': ['wcon_schema*.json']},
      packages=['owmeta_movement'])
