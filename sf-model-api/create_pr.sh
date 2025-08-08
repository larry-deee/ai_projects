#!/bin/bash

# Ensure we're on the correct branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "feat/openai-frontdoor-adapters" ]; then
    echo "Error: Not on feat/openai-frontdoor-adapters branch"
    exit 1
fi

# Check if we have the gh CLI tool
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed. Please install it first:"
    echo "  brew install gh"
    echo "  or visit https://cli.github.com/"
    exit 1
fi

# Push branch to remote
echo "Pushing branch to remote..."
git push origin feat/openai-frontdoor-adapters

# Read the PR description from our file
PR_BODY=$(cat PR_DESCRIPTION.md)

# Create pull request using gh CLI
echo "Creating pull request..."
gh pr create --title "OpenAI Front-Door & Backend Adapters Architecture" --body "$PR_BODY" --base main

echo "Pull request created successfully!"
echo "To view the PR, run: gh pr view --web"