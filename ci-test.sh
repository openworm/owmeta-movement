#!/bin/sh -x

pytest --cov=./owmeta_movement -m 'not inttest'
