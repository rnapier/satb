# SATB

A command-line tool for processing MusicXML files for SATB choral arrangements.

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. To install and run:

```bash
# Install dependencies
uv sync

# Run the application
uv run satb --help
```

## Usage

```bash
# Show help
uv run satb --help

# Show version
uv run satb --version

# Run with verbose output
uv run satb --verbose

# Process a MusicXML file (functionality not yet implemented)
uv run satb path/to/file.xml
```

## Dependencies

- Python >= 3.9
- music21 >= 8.3.0

## Development Status

This is currently a basic stub application. The command-line interface is set up and ready for development, but MusicXML processing functionality has not yet been implemented.

## Future Features

This tool is intended to perform various operations on MusicXML files for SATB (Soprano, Alto, Tenor, Bass) choral arrangements.