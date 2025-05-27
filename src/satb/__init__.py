"""
SATB - A command-line tool for processing MusicXML files for SATB choral arrangements

This module provides functionality for extracting individual voice parts from SATB (Soprano, Alto, Tenor, Bass)
choral arrangements in MusicXML format. It can create separate files for each voice part or combine them
into a single 4-part score with proper part assignments.

The tool handles voice extraction, lyric propagation between voices, and proper handling of musical elements
like ties, slurs, and dynamics.
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

# Define the part/voice mappings for SATB
# Each tuple contains (part_number, voice_number, voice_name)
# - part_number: The part in the score (1-based)
# - voice_number: The voice within that part (1-based)
# - voice_name: The name of the voice part
VOICE_MAPPINGS = [
    (1, 1, "Soprano"),
    (1, 2, "Alto"),
    (2, 5, "Tenor"),
    (2, 6, "Bass")
]


def extract_part_voice(score: music21.stream.Score, part_number: int, voice_number: int, lyrics_stream: Optional[music21.stream.Stream]) -> music21.stream.Score:
    """Filter a Score to contain only the specified part and voice.
    
    This function extracts a single voice from a multi-voice score. It removes all parts except
    the specified one, then removes all voices from that part except the specified voice.
    It also handles stem directions, ties, slurs, and lyrics propagation.
    
    Args:
        score: The input Score object
        part_number: The part number to keep (1-based)
        voice_number: The voice number to keep within that part (1-based)
        lyrics_stream: Optional stream containing lyrics to copy to notes without lyrics.
                      Typically the soprano part is used as the lyrics source.
    
    Returns:
        A new Score containing only the specified part and voice
    
    Raises:
        ValueError: If the part_number is out of range
    """
    # Make a deep copy to avoid modifying the original
    score = copy.deepcopy(score)
    
    # Validate part number
    if part_number < 1 or part_number > len(score.parts):
        raise ValueError(f"Part number {part_number} is out of range (1-{len(score.parts)})")
    
    # Save the Spanners to reapply
    spanners = copy.deepcopy(score.parts[0].spanners.stream())

    # Remove all parts except the specified one (minus one for 1-offset)
    keep_part = score.parts[part_number - 1]
    for p in list(score.parts):
        if p is not keep_part:
            score.remove(p, recurse=True)
    
    # Now strip the remaining part to only the specified voice
    voice_id = str(voice_number)
    for v in list(score.recurse().voices):
        if v.id != voice_id:
            score.remove(v, recurse=True)

    # Reinsert the spanners
    score.parts[0].insert(0, spanners)

    for n in score.recurse().notes:
        # Remove stem direction specifications
        n.stemDirection = None

        # FIXME: Maybe not just lyrics[0]?
        # BUG: We're getting extension too far into the beginning Measure 15, and in the Bass of 16
        # Extend ties and slurs to lyrics.
        # This is a bug in Music21; doesn't support <extend>
        # https://github.com/cuthbertLab/music21/issues/516
        if n.lyrics:
            if n.tie:
                if n.tie.type == 'start':
                    n.lyrics[0].syllabic = 'begin'
                elif n.tie.type == 'continue':
                    n.lyrics[0].syllabic = 'middle'
                elif n.tie.type == 'stop':
                    n.lyrics[0].syllabic = 'end'
            else:
                # FIXME: This is ugly code
                spans = n.getSpannerSites()
                for span in spans:
                    if isinstance(span, music21.spanner.Slur):
                        if span[0] == n:
                            n.lyrics[0].syllabic = 'begin'
                        elif span[-1] == n:
                            n.lyrics[0].syllabic = 'end'
                        else:
                            n.lyrics[0].syllabic = 'middle'
    
    # Copy lyrics and from first (usually Soprano) voice if available and current note has no lyric
    if lyrics_stream is not None:

        lyrics_in = lyrics_stream.recurse().notes.stream()
        lyrics_out = score.recurse().notes.stream()

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


# TODO: Do I need to create a new wedge and insert it in this part?
                    # for span in corresponding_notes[0].getSpannerSites():
                    #     if isinstance(span, music21.dynamics.DynamicWedge):
                    #         print(f"FOUND wedge (voice: {voice_number})")
                    #         # FIXME: Maybe check if we already have a dynamic?
                    #         span.addSpannedElements(n)
                    #     else:
                    #         print(f"FOUND span: {span}")


    return score


def extract_voice_to_part(score: music21.stream.Score, part_number: int, voice_number: int, part_name: str, lyrics_stream: Optional[music21.stream.Stream]) -> music21.stream.Part:
    """Extract a voice from a score and return it as a standalone Part.
    
    This function extracts a single voice and converts it to a standalone part with
    the specified name. It uses extract_part_voice internally to filter the score.
    
    Args:
        score: The input Score object
        part_number: The part number containing the voice (1-based)
        voice_number: The voice number to extract (1-based)
        part_name: Name for the extracted part
        lyrics_stream: Optional stream containing lyrics to copy to notes without lyrics.
                      Typically the soprano part is used as the lyrics source.
    
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
    
    Extracts all 4 voices into separate parts based on VOICE_MAPPINGS. This function
    creates a new score with four separate parts (Soprano, Alto, Tenor, Bass) from
    a score that may have combined voices within parts. It preserves metadata from
    the original score and copies lyrics from the soprano part to other parts when needed.
    
    Args:
        score: The input Score object with combined voices
    
    Returns:
        A new Score with 4 separate parts (S, A, T, B)
    """
    # Create new score
    result_score = music21.stream.Score()
    
    # Copy metadata from original
    if score.metadata:
        result_score.metadata = copy.deepcopy(score.metadata)

    # Music21 sets this to the filename by default.
    result_score.metadata.movementName = None

    # Extract each voice as a separate part using the global voice mappings
    
    # # First extract the first part (for lyrics)
    # first_part_num, first_voice_num, first_voice_name = VOICE_MAPPINGS[0]
    # first_part = extract_voice_to_part(score, first_part_num, first_voice_num, first_voice_name, None)
    # result_score.append(first_part)
    
    # Then extract the remaining parts
    first_part = None
    for part_num, voice_num, voice_name in VOICE_MAPPINGS:
        part = extract_voice_to_part(score, part_num, voice_num, voice_name, first_part)
        if not first_part:
            first_part = part
        result_score.append(part)
    
    return result_score

def process_separate_files(score: music21.stream.Score, file_path: Path) -> None:
    """Process a score into separate files for each voice.
    
    This function extracts each voice from the score and saves it as a separate MusicXML file.
    The output files are named using the original filename with the voice name appended
    (e.g., "score-Soprano.musicxml"). The soprano part is extracted first and used as a
    source for lyrics in the other parts.
    
    Args:
        score: The input Score object
        file_path: Path to the original file
    
    Raises:
        Exception: If there's an error processing the first voice, the function will exit.
                  Errors in other voices will be reported but processing will continue.
    """
    print("Creating separate files for each voice...")
    
    # First extract the first voice to use as lyrics source
    first_part_num, first_voice_num, first_voice_name = VOICE_MAPPINGS[0]
    try:
        first_voice_score = extract_part_voice(score, first_part_num, first_voice_num, None)
        
        # Save the first voice
        output_filename = file_path.stem + f"-{first_voice_name}" + file_path.suffix
        output_path = file_path.parent / output_filename
        first_voice_score.write('musicxml', fp=output_path)
        
        print(f"Filtered score (Part {first_part_num}, Voice {first_voice_num}) saved to: {output_filename}")
        
        # Process remaining voices
        for part_num, voice_num, voice_name in VOICE_MAPPINGS[1:]:
            try:
                filtered_score = extract_part_voice(score, part_num, voice_num, first_voice_score)
                
                # Save the filtered result
                output_filename = file_path.stem + f"-{voice_name}" + file_path.suffix
                output_path = file_path.parent / output_filename
                filtered_score.write('musicxml', fp=output_path)
                
                print(f"Filtered score (Part {part_num}, Voice {voice_num}) saved to: {output_filename}")
                
            except Exception as e:
                print(f"Error processing Part {part_num}, Voice {voice_num} ({voice_name}): {e}", file=sys.stderr)
                # Continue with other voices even if one fails
                continue
                
    except Exception as e:
        print(f"Error processing first voice: {e}", file=sys.stderr)
        sys.exit(1)


def process_combined_file(score: music21.stream.Score, file_path: Path) -> None:
    """Process a score into a single 4-part score.
    
    This function creates a new 4-part score from the input score, with each voice
    (Soprano, Alto, Tenor, Bass) in its own part. The output file is named using
    the original filename with "-4part" appended (e.g., "score-4part.musicxml").
    
    Args:
        score: The input Score object
        file_path: Path to the original file
    
    Raises:
        Exception: If there's an error creating the 4-part score, the function will exit.
    """
    print("Creating single 4-part score...")
    
    try:
        # Convert to 4-part score
        four_part_score = create_single_4part_score(score)
        
        # Save the result
        output_filename = file_path.stem + "-4part" + file_path.suffix
        output_path = file_path.parent / output_filename
        four_part_score.write('musicxml', fp=output_path)
        
        print(f"4-part score saved to: {output_filename}")
        
    except Exception as e:
        print(f"Error creating 4-part score: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the SATB command-line tool.
    
    Parses command-line arguments and processes the specified MusicXML file.
    If no file is specified, displays help information.
    
    Command-line options:
        file: Path to the MusicXML file to process
        --separate: Create separate files for each voice instead of a combined 4-part score
    """
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
        '--separate',
        action='store_true',
        help='Create separate files for each voice (Soprano, Alto, Tenor, Bass)'
    )
    
    args = parser.parse_args()
    
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
            score = music21.converter.parse(file_path)
            assert isinstance(score, music21.stream.Score)
        except Exception as e:
            print(f"Error parsing file: {e}", file=sys.stderr)
            sys.exit(1)

        if args.separate:
            process_separate_files(score, file_path)
        else:
            process_combined_file(score, file_path)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

