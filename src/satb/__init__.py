"""
SATB - A command-line tool for processing MusicXML files for SATB choral arrangements
"""

import argparse
import copy
import sys
from pathlib import Path
from typing import Optional

try:
    import music21
except ImportError:
    print("Error: music21 library is required but not installed.", file=sys.stderr)
    sys.exit(1)


def extract_part_voice(score: music21.stream.Score, part_number: int, voice_number: int, lyrics_stream: Optional[music21.stream.Stream]) -> music21.stream.Score:
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
    
    # Save the Spanners to reapply
    spanners = copy.deepcopy(score_copy.parts[0].spanners.stream())

    # Remove all parts except the specified one
    parts_to_remove = []
    for i, part in enumerate(score_copy.parts):
        if i != (part_number - 1):  # Convert to 0-based index
            parts_to_remove.append(part)
    
    for part in parts_to_remove:
        score_copy.remove(part)
    
    # Now strip the remaining part to only the specified voice
    voice_id = str(voice_number)
    
    # for meas in target_part.measures():
    voices_to_remove = []
    for v in score_copy.recurse().voices:
        if v.id != voice_id:
            voices_to_remove.append(v)
    
    for v in voices_to_remove:
        score_copy.remove(v, recurse=True)

    # Reinsert the spanners
    score_copy.parts[0].insert(0, spanners)

    # Remove stem direction specifications
    for n in score_copy.recurse().notes:
        n.stemDirection = None

        # FIXME: Maybe not just lyrics[0]
        if n.lyrics:
            if n.tie:
                if n.tie.type == 'start':
                    n.lyrics[0].syllabic = 'begin'
                elif n.tie.type == 'continue':
                    n.lyrics[0].syllabic = 'middle'
                elif n.tie.type == 'stop':
                    n.lyrics[0].syllabic = 'end'

    
    # Copy lyrics from Soprano voice if available and current note has no lyric
    if lyrics_stream is not None:

        lyrics_in = lyrics_stream.recurse().notes.stream()
        lyrics_out = score_copy.recurse().notes.stream()

        for note in lyrics_out:
            # Check if note has no lyric
            if not note.lyric and (note.tie == None or note.tie.type == 'start'):
                # Find the equivalent note in first_voice using offset
                offset = note.getOffsetBySite(lyrics_out)
                corresponding_notes = lyrics_in.getElementsByOffset(offset)

                if corresponding_notes:
                    # Get the first corresponding note and copy its lyric if it exists
                    first_note = corresponding_notes[0]
                    if first_note.lyrics:
                        note.lyrics = first_note.lyrics
    
    return score_copy


def extract_voice_to_part(score: music21.stream.Score, part_number: int, voice_number: int, part_name: str, lyrics_stream: Optional[music21.stream.Stream]) -> music21.stream.Part:
    """Extract a voice from a score and return it as a standalone Part.
    
    Args:
        score: The input Score object
        part_number: The part number containing the voice (1-based)
        voice_number: The voice number to extract (1-based)
        part_name: Name for the extracted part
    
    Returns:
        A Part containing only the specified voice
    """
    # Use existing function to get a score with just this voice
    voice_score = extract_part_voice(score, part_number, voice_number, lyrics_stream)
    
    # Get the part and rename it
    extracted_part = voice_score.parts[0]
    extracted_part.partName = part_name
    extracted_part.partAbbreviation = part_name
    
    return extracted_part

def create_single_4part_score(score: music21.stream.Score) -> music21.stream.Score:
    """Convert a combined SATB score to a 4-part score with separate parts.
    
    Extracts all 4 voices into separate parts: Soprano, Alto, Tenor, Bass.
    
    Args:
        score: The input Score object with combined voices
    
    Returns:
        A new Score with 4 separate parts
    """
    # Create new score
    result_score = music21.stream.Score()
    
    # Copy metadata from original
    if score.metadata:
        result_score.metadata = copy.deepcopy(score.metadata)

    # Music21 sets this to the filename by default.
    result_score.metadata.movementName = None

    # Extract each voice as a separate part
    # Based on the voice mappings from the existing code:
    # Soprano: Part 1, Voice 1
    # Alto: Part 1, Voice 2
    # Tenor: Part 2, Voice 5
    # Bass: Part 2, Voice 6
    
    soprano_part = extract_voice_to_part(score, 1, 1, "Soprano", None)
    alto_part = extract_voice_to_part(score, 1, 2, "Alto", soprano_part)
    tenor_part = extract_voice_to_part(score, 2, 5, "Tenor", soprano_part)
    bass_part = extract_voice_to_part(score, 2, 6, "Bass", soprano_part)
    
    # Add parts to the new score in SATB order
    result_score.append(soprano_part)
    result_score.append(alto_part)
    result_score.append(tenor_part)
    result_score.append(bass_part)
    
    return result_score

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
    
    parser.add_argument(
        '--separate',
        action='store_true',
        help='Create separate files for each voice (Soprano, Alto, Tenor, Bass)'
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
        
        # Parse the file
        print(f"Processing file: {args.file}")
        try:
            score = music21.converter.parse(str(file_path))
        except Exception as e:
            print(f"Error parsing file: {e}", file=sys.stderr)
            sys.exit(1)

        if args.separate:
            # Create separate files for each voice
            print("Creating separate files for each voice...")
            
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
            # Create a single 4-part score (default behavior)
            print("Creating single 4-part score...")
            
            try:
                # Convert to 4-part score
                four_part_score = create_single_4part_score(score)
                
                # Save the result
                output_filename = file_path.stem + "-4part" + file_path.suffix
                output_path = file_path.parent / output_filename
                four_part_score.write('musicxml', fp=str(output_path))
                
                print(f"4-part score saved to: {output_filename}")
                
                if args.verbose:
                    print(f"\n4-part score contains {len(four_part_score.parts)} parts:")
                    for i, part in enumerate(four_part_score.parts, 1):
                        part_name = part.partName or f"Part {i}"
                        notes = list(part.recurse().getElementsByClass(['Note', 'Chord']))
                        print(f"  Part {i}: {part_name} - {len(notes)} notes/chords")
                
            except Exception as e:
                print(f"Error creating 4-part score: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
