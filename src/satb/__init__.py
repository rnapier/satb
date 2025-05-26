"""
SATB - A command-line tool for processing MusicXML files for SATB choral arrangements
"""

import argparse
import sys
from pathlib import Path

try:
    import music21
except ImportError:
    print("Error: music21 library is required but not installed.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    """Main entry point for the SATB command-line tool."""
    parser = argparse.ArgumentParser(
        prog='satb',
        description='A command-line tool for processing MusicXML files for SATB choral arrangements'
    )
    
    parser.add_argument(
        'file',
        nargs='?',
        help='MusicXML file to process'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"SATB v0.1.0")
        print(f"Using music21 v{music21.VERSION_STR}")
    
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)
        
        if not file_path.suffix.lower() in ['.xml', '.musicxml', '.mxl']:
            print(f"Warning: '{args.file}' may not be a MusicXML file.")
        
        print(f"Processing file: {args.file}")
        print("(Processing functionality not yet implemented)")
    else:
        print("SATB - MusicXML processor for SATB choral arrangements")
        print("Usage: satb <file.xml> [options]")
        print("Run 'satb --help' for more information.")


if __name__ == '__main__':
    main()
