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


def process_musicxml_file(file_path: Path, verbose: bool = False) -> None:
    """Process a MusicXML file and display its top-level structures."""
    try:
        # Parse the file using music21
        score = music21.converter.parse(str(file_path))
        
        print("\n=== Top-Level Structure Analysis ===")
        
        # Basic file information
        print(f"Title: {score.metadata.title or 'Not specified'}")
        print(f"Composer: {score.metadata.composer or 'Not specified'}")
        
        # Get all parts
        parts = score.parts
        print(f"\nNumber of parts: {len(parts)}")
        
        for i, part in enumerate(parts, 1):
            part_name = part.partName or f"Part {i}"
            instrument = part.getInstrument()
            instrument_name = instrument.instrumentName if instrument is not None else "Unknown"
            
            print(f"  Part {i}: {part_name} ({instrument_name})")
            
            # Count measures and notes using recurse()
            measures = list(part.recurse().getElementsByClass(music21.stream.Measure))
            notes = list(part.recurse().getElementsByClass(['Note', 'Chord']))
            
            print(f"    Measures: {len(measures)}")
            print(f"    Notes/Chords: {len(notes)}")
            
            if verbose:
                # Show key signature and time signature
                key_sig = list(part.recurse().getElementsByClass(music21.key.KeySignature))
                time_sig = list(part.recurse().getElementsByClass(music21.meter.TimeSignature))
                
                if key_sig:
                    print(f"    Key signature: {key_sig[0]}")
                if time_sig:
                    print(f"    Time signature: {time_sig[0]}")
        
        # Overall score information using recurse()
        all_notes = list(score.recurse().getElementsByClass(['Note', 'Chord']))
        print(f"\nTotal notes/chords in score: {len(all_notes)}")
        
        # Get key and time signatures from the score
        key_signatures = list(score.recurse().getElementsByClass(music21.key.KeySignature))
        time_signatures = list(score.recurse().getElementsByClass(music21.meter.TimeSignature))
        
        if key_signatures:
            print(f"Key signature: {key_signatures[0]}")
        if time_signatures:
            print(f"Time signature: {time_signatures[0]}")
        
        # Analyze if this looks like SATB
        if len(parts) == 4:
            print("\n=== SATB Analysis ===")
            print("This appears to be a 4-part score (potentially SATB)")
            
            for i, part in enumerate(parts):
                part_name = part.partName or f"Part {i+1}"
                
                # Get the range of notes in this part using recurse()
                notes = list(part.recurse().getElementsByClass(['Note', 'Chord']))
                if notes:
                    pitches = []
                    for note in notes:
                        if note.pitch is not None:
                            pitches.append(note.pitch)
                        elif getattr(note, 'pitches', None) is not None:  # chord
                            pitches.extend(note.pitches)
                    
                    if pitches:
                        lowest = min(pitches, key=lambda p: p.midi)
                        highest = max(pitches, key=lambda p: p.midi)
                        print(f"  {part_name}: Range {lowest.name}{lowest.octave} - {highest.name}{highest.octave}")
        
        # Output all notes in Part 1, Voice 1
        if parts:
            print("\n=== Part 1, Voice 1 Notes ===")
            part1 = parts[0]
            
            # Strip to only Part 1, Voice 1 using the pattern from rules
            score_copy = copy.deepcopy(score)
            
            # Remove all parts except Part 1
            parts_to_remove = []
            for i, part in enumerate(score_copy.parts):
                if i != 0:  # Keep only the first part (index 0)
                    parts_to_remove.append(part)
            
            for part in parts_to_remove:
                score_copy.remove(part)
            
            # Now strip Part 1 to only Voice 1
            part1_copy = score_copy.parts[0]
            for meas in part1_copy.getElementsByClass(music21.stream.Measure):
                voices = meas.getElementsByClass(music21.stream.Voice)
                for v in voices:
                    if v.id != '1':
                        meas.remove(v)
            
            voice1_notes = list(part1_copy.recurse().getElementsByClass(['Note', 'Chord']))
            
            print(f"Found {len(voice1_notes)} notes/chords in Voice 1:")
            
            for i, note in enumerate(voice1_notes, 1):
                measure = note.getContextByClass(music21.stream.Measure)
                measure_num = measure.number if measure else "?"
                offset = note.offset if note.offset is not None else 0.0
                
                if note.isNote:
                    pitch_info = f"{note.pitch.name}{note.pitch.octave}"
                    duration_info = f"{note.duration.quarterLength}ql"
                    print(f"  {i:3d}. M{measure_num:2} @{offset:4.1f}: {pitch_info:4s} ({duration_info})")
                elif note.isChord:
                    pitch_names = [f"{p.name}{p.octave}" for p in note.pitches]
                    pitch_info = "[" + ", ".join(pitch_names) + "]"
                    duration_info = f"{note.duration.quarterLength}ql"
                    print(f"  {i:3d}. M{measure_num:2} @{offset:4.1f}: {pitch_info} ({duration_info})")
                else:
                    duration_info = f"{note.duration.quarterLength}ql" if note.duration else "?"
                    print(f"  {i:3d}. M{measure_num:2} @{offset:4.1f}: REST ({duration_info})")
            
            # Output the filtered score to a new MusicXML file
            output_filename = file_path.stem + "-Soprano" + file_path.suffix
            output_path = file_path.parent / output_filename
            score_copy.write('musicxml', fp=str(output_path))
            print(f"\nFiltered score saved to: {output_filename}")
        else:
            print("\n=== Part 1, Voice 1 Notes ===")
            print("No parts found in the score")
        
    except Exception as e:
        print(f"Error parsing file: {e}", file=sys.stderr)
        sys.exit(1)


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
        
        process_voices_to_parts(file_path, args.verbose)
    else:
        print("SATB - MusicXML processor for SATB choral arrangements")
        print("Usage: satb <file.xml> [options]")
        print("Run 'satb --help' for more information.")


if __name__ == '__main__':
    main()
