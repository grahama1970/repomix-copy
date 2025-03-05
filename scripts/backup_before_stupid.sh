#!/bin/bash

# Use before you do somethin stupid/significant

# Create a tagged stable backup point
git tag -a stable-backup -m "Stable project state before significant changes"

# Create and switch to a backup branch
git checkout -b backup-before-changes

# Optional: Push tag and branch to remote repository
git push origin stable-backup
git push -u origin backup-before-changes