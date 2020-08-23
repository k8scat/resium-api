#!/bin/bash

branch=$1
if [ -z "$branch" ];then
  branch=master
fi

remotes=$2
if [ -n "$remotes" ];then
  echo "remotes: $remotes"
  for remote in ${remotes//,/ };do
    echo "git push $remote $branch"
    git push "$remote" "$branch"
  done
else
  for remote in $(git remote);do
    echo "git push $remote $branch"
    git push "$remote" "$branch"
  done
fi

