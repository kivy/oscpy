#!/usr/bin/env bash
set -ex

if [[ "refs/tags/$(git tag | grep v | tail -n 1)" = $GITHUB_REF ]]; then
    pip install -U setuptools wheel twine
    python setup.py sdist bdist_wheel
    python -m twine check dist/*
  if [[ $GITHUB_REF =~ -test$ ]]; then
    python -m twine upload --disable-progress-bar --repository-url https://test.pypi.org/legacy/ dist/*
  else
    echo "OOF this would have uploaded"
    # python -m twine upload --disable-progress-bar dist/*
  fi
fi
