#!/bin/sh -x

pip install --upgrade pip
pip install '.[plot]'
pip install --upgrade -r test-requirements.txt
