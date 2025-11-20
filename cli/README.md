# Solvigo CLI

Interactive CLI tool for managing Solvigo client projects on Google Cloud Platform.

## Installation

From the platform repository root:

```bash
cd cli
pip install -e .
```

This makes the `solvigo` command available globally.

## Environment Setup

To use the CLI from any directory (not just the platform repository), set the platform root:

```bash
export SOLVIGO_PLATFORM_ROOT="/Users/kristifrancis/Desktop/Solvigo/create-app"
```

**Make it permanent** by adding to your shell profile:

```bash
# For zsh (macOS default)
echo 'export SOLVIGO_PLATFORM_ROOT="/Users/kristifrancis/Desktop/Solvigo/create-app"' >> ~/.zshrc
source ~/.zshrc

# For bash
echo 'export SOLVIGO_PLATFORM_ROOT="/Users/kristifrancis/Desktop/Solvigo/create-app"' >> ~/.bashrc
source ~/.bashrc
```

**Or** source the platform config file:

```bash
source /Users/kristifrancis/Desktop/Solvigo/create-app/.solvigo_config
```

This allows you to run `solvigo` from anywhere on your system!

## Usage

### Interactive Mode (Recommended)

Simply run:

```bash
solvigo
```

The CLI will detect your context and guide you through the available options.

### From Project Directory

```bash
cd clients/acme-corp/app1/
solvigo
```

Output:
```
📂 Project detected: acme-corp/app1

What would you like to do?
  1. Add services to Terraform
  2. Deploy infrastructure
  3. View project status
  ...
```

### From Anywhere

```bash
solvigo
```

Output:
```
No project detected.

What would you like to do?
  1. Create new project
  2. Choose existing project
  3. Import existing GCP project
  ...
```

## Commands

While the CLI is primarily interactive, you can also use direct commands:

```bash
solvigo init <client> <project>     # Create new project
solvigo import <gcp-project-id>     # Import existing GCP project
solvigo deploy                      # Deploy infrastructure
solvigo status                      # View project status
solvigo discover <gcp-project-id>   # Discover resources in GCP project
```

## Features

### CI/CD Integration (NEW!)
The CLI now supports automated Cloud Build CI/CD setup:
- ✅ Interactive prompts for backend/frontend/fullstack applications
- ✅ Dockerfile location selection with directory browsing
- ✅ Automatic generation of `cicd.tf` and `cloudbuild.yaml`
- ✅ Integration with platform Cloud Build infrastructure
- ✅ Support for dev/staging/prod environments

When you import or create a project, you'll be prompted to set up CI/CD with:
1. Application type selection (backend/frontend/fullstack)
2. Dockerfile location for each service
3. Cloud Run service naming
4. GitHub repository URL
5. Environment selection

The CLI generates all necessary configuration files automatically!

## Development

### Setup Development Environment

```bash
cd cli
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black solvigo/
flake8 solvigo/
mypy solvigo/
```

## Project Structure

```
cli/
├── solvigo/
│   ├── main.py              # Entry point
│   ├── commands/            # Command handlers
│   │   ├── interactive.py   # Main interactive mode
│   │   ├── init.py          # Project creation
│   │   ├── import_cmd.py    # Import existing
│   │   └── ...
│   ├── ui/                  # User interface
│   │   ├── prompts.py       # Interactive prompts
│   │   └── display.py       # Rich console displays
│   ├── gcp/                 # GCP integration
│   │   ├── discovery.py     # Resource discovery
│   │   └── projects.py      # Project management
│   ├── terraform/           # Terraform generation
│   │   ├── generator.py     # Code generation
│   │   └── runner.py        # Terraform execution
│   └── utils/               # Utilities
│       ├── context.py       # Context detection
│       └── config.py        # Configuration
└── tests/
```

## Configuration

The CLI uses configuration from:

1. Environment variables (`.solvigo_config`)
2. Platform repository structure
3. GCP authentication (via gcloud)

## Requirements

- Python 3.11+
- gcloud CLI installed and authenticated
- Terraform >= 1.5.0
- Access to Solvigo GCP organization

## Examples

See `/docs/cli-interactive-flows.md` for detailed usage examples.
