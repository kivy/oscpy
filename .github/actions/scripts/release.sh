#!/usr/bin/env bash
set -ex

if [[ ! $GITHUB_REF =~ ^refs/tags/ ]]; then
   exit 0
fi

owner=kivy
repository=oscpy
access_token=$GITHUB_TOKEN

changelog_lines=$(grep -n "===" CHANGELOG | head -n2 | tail -n1 | cut -d':' -f1)

changelog=$(head -n $(( $changelog_lines - 2)) CHANGELOG | awk '{printf("%s\\n",$0)} END {print ""}')

tag=${GITHUB_REF#refs/tags/}
draft="false"
prerelease="false"
version_name="$tag"
message="Release $tag"

pip install -U setuptools wheel twine
python setup.py sdist bdist_wheel
python -m twine check dist/*

twine="python -m twine upload --disable-progress-bar"

if [[ $GITHUB_REF =~ -test$ ]]; then
    twine="$twine --repository-url https://test.pypi.org/legacy/"
    draft="true"
    prerelease="true"
    message="test release $tag"
fi

API_JSON="{
    \"tag_name\": \"$tag\",
    \"name\": \"$version_name\",
    \"body\": \"$message\n$changelog\",
    \"draft\": $draft,
    \"prerelease\": $prerelease
}"

echo $API_JSON

$twine dist/*
curl --data "$API_JSON"\
     Https://api.github.com/repos/$owner/$repository/releases?access_token=$access_token
