#!/bin/sh -ex

pytest --cov=./owmeta_movement -m 'not inttest'
pytest --cov=./owmeta_movement --cov-append -m 'inttest'
