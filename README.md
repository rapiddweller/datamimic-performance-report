# DATAMIMIC Performance Report

DATAMIMIC Performance Report is a CLI tool designed to run and analyze performance tests for DATAMIMIC operations. The project allows you to execute synthetic data generation scripts (XML based) under different configurations, measure key performance metrics (elapsed time, memory usage, throughput), and generate consolidated HTML reports.

## Table of Contents

- [DATAMIMIC Performance Report](#datamimic-performance-report)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Running Performance Tests](#running-performance-tests)
  - [Project Structure](#project-structure)
  - [Configuration](#configuration)
  - [Contributing](#contributing)
  - [License](#license)

## Introduction

This project is aimed at providing an end-to-end performance testing solution for DATAMIMIC operations. It supports:
- Executing various XML test scripts that mimic real data scenarios.
- Configuring tests (e.g., record counts, exporters, process counts) via command-line options or a YAML configuration file.
- Automatically installing specific versions of the `DATAMIMIC-CE` component from PyPI (or TestPyPI) as part of the test runs.
- Capturing performance metrics like elapsed execution time and peak memory usage.
- Aggregating collected data to generate comprehensive HTML reports for throughput and memory consumption analysis.

## Features

- **Performance Testing:** Run tests over multiple configurations such as different record counts, process counts, and DATAMIMIC-CE versions.
- **Flexible Configuration:** Override default parameters via a YAML configuration file or environment variables (e.g., `DATAMIMIC_VERSIONS`).
- **Automated Installation:** Dynamically install specified versions of `DATAMIMIC-CE` before running a test.
- **Detailed Reporting:** Generate consolidated HTML reports that include both raw and interpolated performance data.
- **Modular & Extensible:** Built with an emphasis on maintainability and performance. Core functionality is organized into separate modules for CLI, performance measurement, data processing, and report generation.

## Requirements

- **Python:** 3.11 or newer
- **Dependencies:**  
  - `typer-cli` (>= 0.15.1)
  - `psutil` (>= 5.9.0)
  - `loguru` (>= 0.6.0)
  - `jinja2` (>= 3.1.5)
  - `matplotlib` (>= 3.10.0)
  - `pip` (>= 25.0.1)
  - `setuptools` (>= 75.8.0)
  - `wheel` (>= 0.42.0)

*Refer to the [pyproject.toml](pyproject.toml) file for the complete dependency list and project configuration.*

## Installation

1. **Clone the Repository:**
    ```bash
    git clone https://your-repo-url.git
    cd DATAMIMIC-performance-report
    ```

2. **(Optional) Create and Activate a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install Dependencies using uv sync:**
    ```bash
    uv sync install
    ```

## Usage

The CLI entry point is defined in `app/main.py` and is exposed as the `datamimic-perf` command (as set in `pyproject.toml`).

### Running Performance Tests

Run performance tests using the `run` command. This command accepts several options:

- `--config`: Path to a YAML configuration file (to override default parameters).
- `--counts`: List of record counts (default: `[100000, 200000, 300000]`).
- `--exporters`: List of exporters (default: `["CSV"]`).
- `--num-processes`: List of process counts (default: `[1, 4]`).
- `--versions`: List of `DATAMIMIC-ce` versions to test (default: `["1.2.1.dev2", "1.2.2.dev23"]`).
- `--iterations`: Number of iterations per configuration (default: `1`).
- `--script`: (Optional) Specific script filename to test (e.g., `test_datetime.xml`).

**Example command:**

```bash
datamimic-perf run --config config.yaml --counts 100000 200000 300000 --exporters CSV --num-processes 1 4 --versions 1.2.1.dev2 1.2.2.dev23 --iterations 1 --script test_datetime.xml
```

This command will:
- Parse JSON result files available in the `results` directory.
- Aggregate performance metrics by version.
- Produce an HTML report with data visualizations on throughput and memory consumption.

## Project Structure

```bash
.
├── pyproject.toml # Project configuration and dependency management.
├── README.md # This file.
└── app
├── main.py # CLI entry point using Typer.
├── report_components # Modules for data processing and report generation.
│ ├── data_processor.py # Processes throughput and memory data.
│ ├── interpolation.py # Provides interpolation utility functions.
│ └── report_generator.py # Generates the consolidated HTML report.
├── scripts # XML test scripts representing various data generation tests.
│ ├── test_datetime.xml
│ ├── test_entities.xml
│ └── test_entity_file.xml
└── utils
└── performance_utils.py # Performs performance measurements and test executions.
```

## Configuration

You can override the default testing parameters using a YAML configuration file. The configuration can include:
- `counts`: List of record counts.
- `exporters`: List of exporters to use.
- `num_processes`: List of process counts.
- `iterations`: Number of test iterations.
- `versions`: List of `DATAMIMIC-ce` versions to test.

When the `--config` option is provided to the `run` command, these settings will replace the default parameters. Additionally, the `DATAMIMIC_VERSIONS` environment variable (if set) will override any version setting you pass.

## Contributing

Contributions are welcome! Please adhere to the following guidelines:
- **Do not remove or reduce existing documentation strings.** Improve them only.
- **Do not change input/output behaviors** of functions unless explicitly required.
- **Preserve the existing logic** while proposing improvements for better architecture and maintainability.
- When writing unit tests, follow Ian Cooper’s TDD approach:
  - Reuse existing unit test utilities.
  - Create new ones if needed.
- Ensure that all your changes are well tested.
- Before submitting pull requests, please run all tests to avoid breaking any functionality.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
