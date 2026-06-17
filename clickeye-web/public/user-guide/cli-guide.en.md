---
title: CLI Guide
description: A guide to installing the ClickEye CLI tool and its main commands.
order: 4
---

# CLI Guide

The ClickEye CLI is a command-line interface for power users. It shares the same generation engine as the web dashboard.

## Installation

```bash
npm install -g @clickeye/cli
```

## Basic Commands

```bash
# Check the version
clickeye --version

# Help
clickeye --help

# Log in
clickeye login

# Create a solution
clickeye create

# List solutions
clickeye list
```

## Creating a Solution

```bash
# Create a solution in interactive mode
clickeye create

# Specify options
clickeye create --platform claude-code --stack nextjs
```

## Configuration File

CLI configuration is stored in `~/.clickeye/config.json`.

```json
{
  "apiUrl": "https://api.clickeye.io",
  "token": "your-api-token"
}
```

> Detailed content will be updated later (24S-186).
