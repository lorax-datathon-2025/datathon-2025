# Contributing Guide

## How to Pull a Team Member's Branch

### Pulling Rivan's Branch

If you want to work with or review Rivan's branch, follow these steps:

#### Option 1: Pull and checkout the branch (recommended if you want to work on it)

```bash
# Fetch all remote branches
git fetch origin

# Checkout Rivan's branch (Git will automatically create a local tracking branch)
git checkout rivan
```

This will create a local copy of Rivan's branch that tracks the remote branch. If you're checking out the branch for the first time and the simple command doesn't work, you can explicitly create the tracking branch:

```bash
git checkout -b rivan origin/rivan
```

#### Option 2: Just fetch to see what's there (without switching branches)

```bash
# Fetch all remote branches
git fetch origin

# View the branch without checking it out
git log origin/rivan

# Or see the differences
git diff origin/rivan
```

#### Option 3: Pull changes if you're already on the branch

```bash
# If you're already on the rivan branch
git pull origin rivan
```

### General Tips

- **List all available branches** (including remote):
  ```bash
  git branch -a
  ```

- **See which branch you're currently on**:
  ```bash
  git branch
  ```

- **Switch between branches**:
  ```bash
  git checkout <branch-name>
  ```

- **Update your branch with latest changes**:
  ```bash
  git pull origin <branch-name>
  ```

## Available Branches

The repository currently has the following branches:
- `main` - The main/production branch
- `rivan` - Rivan's working branch
- `erica` - Erica's working branch
- `ryan` - Ryan's working branch
- `hannah/updates` - Hannah's updates branch
