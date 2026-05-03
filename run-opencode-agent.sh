#!/bin/bash
# run-agent.sh
# Usage: ./run-agent.sh feature-branch-name

BRANCH_NAME=$1

# 1. Make the work tree
git worktree add ../$BRANCH_NAME -b $BRANCH_NAME
cd ../$BRANCH_NAME

# 2. Set local git rule for the token
git config --local url."https://${GITHUB_AGENT_TOKEN}@github.com/".insteadOf "git@github.com:"

# 3. Start the VM (Add your micro VM boot command here)
# echo "Booting VM in $BRANCH_NAME..."
