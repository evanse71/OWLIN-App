# Script to push to a new GitHub repository
# Usage: .\push-to-github.ps1 -RepoUrl "https://github.com/username/repo-name.git"

param(
    [Parameter(Mandatory=$true)]
    [string]$RepoUrl
)

Write-Host "Setting up remote repository..." -ForegroundColor Green
git remote add origin $RepoUrl

Write-Host "Pushing to GitHub..." -ForegroundColor Green
git branch -M main
git push -u origin main

Write-Host "Done! Your code has been pushed to GitHub." -ForegroundColor Green
Write-Host "Repository URL: $RepoUrl" -ForegroundColor Cyan

