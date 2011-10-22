#!/usr/bin/env bash
mkdir -p locale/en/LC_MESSAGES/
msgfmt locale/templates/openastro.pot --output-file=locale/en/LC_MESSAGES/openastro.mo
