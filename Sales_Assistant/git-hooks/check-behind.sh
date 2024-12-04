#!/usr/bin/env bash

# The branch to compare with
COMPARE_BRANCH="dev"

# Fetch latest changes for the compare branch
git fetch origin $COMPARE_BRANCH


# Check if the current branch is behind the compare branch
if ! git merge-base --is-ancestor origin/$COMPARE_BRANCH HEAD; then
    echo "Your branch is behind '$COMPARE_BRANCH'. Please rebase before committing."
    exit 1
fi

# Allow the commit if the branch is not behind
exit 0
