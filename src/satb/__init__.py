"""
SATB - A command-line tool for processing MusicXML files for SATB choral arrangements
"""

import argparse
import copy
import sys
from pathlib import Path

try:
    import music21
except ImportError:
    print("Error: music21 library is required but not installed.", file=sys.stderr)
    sys.exit(1)


def extract_part_voice(score: music21.stream.Score, part_number: int, voice_number: int) -> music21.stream.Score:
    """Filter a Score to contain only the specified part and voice.
    
    Args:
        score: The input Score object
        part_number: The part number to keep (1-based)
        voice_number: The voice number to keep within that part (1-based)
    
    Returns:
        A new Score containing only the specified part and voice
    """
    # Make a deep copy to avoid modifying the original
    score_copy = copy.deepcopy(score)
    
    # Validate part number
    if part_number < 1 or part_number > len(score_copy.parts):
        raise ValueError(f"Part number {part_number} is out of range (1-{len(score_copy.parts)})")
    
    # Remove all parts except the specified one
    parts_to_remove = []
    for i, part in enumerate(score_copy.parts):
        if i != (part_number - 1):  # Convert to 0-based index
            parts_to_remove.append(part)
    
    for part in parts_to_remove:
        score_copy.remove(part)
    
    # Now strip the remaining part to only the specified voice
    target_part = score_copy.parts[0]
    voice_id = str(voice_number)
    
    for meas in target_part.getElementsByClass(music21.stream.Measure):
        voices = meas.getElementsByClass(music21.stream.Voice)
        voices_to_remove = []
        for v in voices:
            if v.id != voice_id:
                voices_to_remove.append(v)
        
        for v in voices_to_remove:
            meas.remove(v)
    
    return score_copy

def process_voices_to_parts(file_path: Path, verbose: bool = False) -> None:
    """Process a MusicXML file using voicesToParts() and save to a new file."""
    try:
        # Parse the file using music21
        score = music21.converter.parse(str(file_path))
        
        print(f"Processing file: {file_path.name}")
        print(f"Title: {score.metadata.title or 'Not specified'}")
        print(f"Composer: {score.metadata.composer or 'Not specified'}")
        
        # Get original part count
        original_parts = len(score.parts)
        print(f"Original parts: {original_parts}")
        
        # Convert voices to parts
        converted_score = score.voicesToParts()
        
        # Get new part count
        new_parts = len(converted_score.parts)
        print(f"Parts after voicesToParts(): {new_parts}")
        
        if verbose:
            print("\n=== Parts Details ===")
            for i, part in enumerate(converted_score.parts, 1):
                part_name = part.partName or f"Part {i}"
                instrument = part.getInstrument()
                instrument_name = instrument.instrumentName if instrument is not None else "Unknown"
                
                notes = list(part.recurse().getElementsByClass(['Note', 'Chord']))
                print(f"  Part {i}: {part_name} ({instrument_name}) - {len(notes)} notes/chords")
        
        # Output the converted score to a new MusicXML file
        output_filename = file_path.stem + "-open" + file_path.suffix
        output_path = file_path.parent / output_filename
        converted_score.write('musicxml', fp=str(output_path))
        print(f"\nConverted score saved to: {output_filename}")
        
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
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
        
        # Parse the file and filter to Part 1, Voice 1 (as default behavior)
        print(f"Processing file: {args.file}")
        try:
            score = music21.converter.parse(str(file_path))
        except Exception as e:
            print(f"Error parsing file: {e}", file=sys.stderr)
            sys.exit(1)

        # Define the part/voice mappings for SATB
        voice_mappings = [
            (1, 1, "Soprano"),
            (1, 2, "Alto"),
            (2, 5, "Tenor"),
            (2, 6, "Bass")
        ]
        
        for part_num, voice_num, voice_name in voice_mappings:
            try:
                filtered_score = extract_part_voice(score, part_num, voice_num)
                
                # Save the filtered result
                output_filename = file_path.stem + f"-{voice_name}" + file_path.suffix
                output_path = file_path.parent / output_filename
                filtered_score.write('musicxml', fp=str(output_path))
                
                print(f"Filtered score (Part {part_num}, Voice {voice_num}) saved to: {output_filename}")
                
            except Exception as e:
                print(f"Error processing Part {part_num}, Voice {voice_num} ({voice_name}): {e}", file=sys.stderr)
                # Continue with other voices even if one fails
                continue
    else:
        print("SATB - MusicXML processor for SATB choral arrangements")
        print("Usage: satb <file.xml> [options]")
        print("Run 'satb --help' for more information.")


if __name__ == '__main__':
    main()
