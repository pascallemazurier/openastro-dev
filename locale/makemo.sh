#!/usr/bin/env bash
mkdir -p ./en/LC_MESSAGES/
msgfmt ./templates/openastro.pot --output-file=./en/LC_MESSAGES/openastro.mo
