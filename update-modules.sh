#!/usr/bin/env bash

git_cmds=(
    'git checkout master'
    'git fetch upstream || true'
    'git fetch origin || true'
    'git merge upstream/master || true'
    'git pull origin master'
)

git submodule update --init --recursive

for git_cmd in "${git_cmds[@]}"; do
    eval git submodule foreach "${git_cmd}"
done
git status
