#!/usr/bin/env bash

if [[ $(git tag | grep v | tail -n 1) = $GITHUB_REF ]]; then
    pip install -U setuptools wheel twine
    python setup.py sdist bdist_wheel
    twine check dist/*
  if [[ $GITHUB_REF =~ ^v.*-test$ ]]; then
    twine upload --disable-progress-bar --repository-url https://test.pypi.org/legacy/ dist/*
  else
    twine upload --disable-progress-bar dist/*
  fi
fi
