"""
SATB - A command-line tool for processing MusicXML files for SATB choral arrangements

This module provides functionality for extracting individual voice parts from SATB (Soprano, Alto, Tenor, Bass)
choral arrangements in MusicXML format. It creates a single 4-part score with proper part assignments.

The tool handles voice extraction, lyric propagation between voices, and proper handling of musical elements
like ties, slurs, and dynamics.
"""

import argparse
import copy
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional

try:
    import music21
except ImportError:
    print("Error: music21 library is required but not installed.", file=sys.stderr)
    sys.exit(1)


# Define a type for voice mappings
class VoiceMapping(NamedTuple):
    """Represents a mapping between a part/voice in the score and a named vocal part.

    Attributes:
        part_number: The part in the score (1-based)
        voice_number: The voice within that part (1-based)
        voice_name: The name of the voice part (e.g., "Soprano", "Alto", etc.)
    """

    part_number: int
    voice_number: int
    voice_name: str


# Define the part/voice mappings for SATB
VOICE_MAPPINGS: List[VoiceMapping] = [
    VoiceMapping(1, 1, "Soprano"),
    VoiceMapping(1, 2, "Alto"),
    VoiceMapping(2, 5, "Tenor"),
    VoiceMapping(2, 6, "Bass"),
]


def inTieOrSlur(note: music21.note.Note, stream: music21.stream.Stream) -> bool:
    if note.tie and note.tie.type != "start":
        return True

    for spanner in stream.recurse().spanners:
        if isinstance(spanner, music21.spanner.Slur) and note in spanner:
            return not spanner.isFirst(note)

    return False


def extract_voice(
    score: music21.stream.Score,
    mapping: VoiceMapping,
    lyrics_stream: Optional[music21.stream.Stream] = None,
) -> music21.stream.Part:
    """Extract a voice from a score and return it as a standalone Part.

    This function extracts a single voice from a multi-voice score and converts it to a
    standalone part with the specified name. It removes all parts except the specified one,
    then removes all voices from that part except the specified voice.
    It also handles stem directions, ties, slurs, and lyrics propagation.

    Args:
        score: The input Score object
        mapping: The VoiceMapping containing part_number, voice_number, and voice_name
        lyrics_stream: Optional stream containing lyrics to copy to notes without lyrics.
                      Typically the soprano part is used as the lyrics source.

    Returns:
        A Part containing only the specified voice
    """

    # Make a copy of the part (move 1-offset to 0-offset)
    part = copy.deepcopy(score.parts[mapping.part_number - 1])

    part.partName = mapping.voice_name
    part.partAbbreviation = mapping.voice_name

    # Now strip the part to only the specified voice
    voice_id = str(mapping.voice_number)
    for v in list(part.recurse().voices):
        if v.id != voice_id:
            part.remove(v, recurse=True)

    # TODO: need to copy slurs first, so inTieOrSlur works

    # Copy lyrics from first (usually Soprano) voice if available and current note has no lyric
    if lyrics_stream is not None:
        lyrics_in = lyrics_stream.recurse().notes.stream()
        lyrics_out = part.recurse().notes.stream()

        for note in lyrics_out:
            # Check if note has no lyric
            if not note.lyric and not inTieOrSlur(note, score):
                # Find the equivalent note in first_voice using offset
                offset = note.getOffsetBySite(lyrics_out)
                corresponding_notes = lyrics_in.getElementsByOffset(offset)

                if corresponding_notes:
                    # Get the first corresponding note and copy its lyric if it exists
                    first_note = corresponding_notes[0]
                    if first_note.lyrics:
                        note.lyrics = first_note.lyrics

    for n in part.recurse().notes:
        # Remove stem direction specifications
        n.stemDirection = None

        # BUG: We're getting extension too far into the beginning Measure 15, and in the Bass of 16
        # Extend ties and slurs to lyrics.
        # This is a bug in Music21; doesn't support <extend>
        # https://github.com/cuthbertLab/music21/issues/516
    #     if n.lyrics:
    #         if n.tie:
    #             if n.tie.type == 'start':
    #                 n.lyrics[0].syllabic = 'begin'
    #             elif n.tie.type == 'continue':
    #                 n.lyrics[0].syllabic = 'middle'
    #             elif n.tie.type == 'stop':
    #                 n.lyrics[0].syllabic = 'end'
    #         else:
    #             # FIXME: This is ugly code
    #             spans = n.getSpannerSites()
    #             for span in spans:
    #                 if isinstance(span, music21.spanner.Slur):
    #                     if span[0] == n:
    #                         n.lyrics[0].syllabic = 'begin'
    #                     elif span[-1] == n:
    #                         n.lyrics[0].syllabic = 'end'
    #                     else:
    #                         n.lyrics[0].syllabic = 'middle'

    return part


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
    first_part = None
    for mapping in VOICE_MAPPINGS:
        part = extract_voice(score, mapping, first_part)
        if not first_part:
            first_part = part
        result_score.append(part)

    return result_score


def process_combined_file(score: music21.stream.Score, file_path: Path) -> None:
    """Process a score into a single 4-part score.

    This function creates a new 4-part score from the input score, with each voice
    (Soprano, Alto, Tenor, Bass) in its own part. The output file is named using
    the original filename with "-4part" appended (e.g., "score-4part.musicxml").

    Args:
        score: The input Score object
        file_path: Path to the original file
    """
    print("Creating single 4-part score...")

    # Convert to 4-part score
    four_part_score = create_single_4part_score(score)

    # Save the result
    output_filename = file_path.stem + "-4part" + file_path.suffix
    output_path = file_path.parent / output_filename
    four_part_score.write("musicxml", fp=output_path)

    print(f"4-part score saved to: {output_filename}")


def main() -> None:
    """Main entry point for the SATB command-line tool.

    Parses command-line arguments and processes the specified MusicXML file.
    If no file is specified, displays help information.

    Command-line options:
        file: Path to the MusicXML file to process
    """
    parser = argparse.ArgumentParser(
        prog="satb",
        description="A command-line tool for processing MusicXML files for SATB choral arrangements",
    )

    parser.add_argument("file", nargs="?", help="MusicXML file to process")

    args = parser.parse_args()

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File '{args.file}' not found.", file=sys.stderr)
            sys.exit(1)

        if not file_path.suffix.lower() in [".xml", ".musicxml", ".mxl"]:
            print(f"Warning: '{args.file}' may not be a MusicXML file.")

        # Parse the file
        print(f"Processing file: {args.file}")
        try:
            score = music21.converter.parse(file_path)
            assert isinstance(score, music21.stream.Score)
        except Exception as e:
            print(f"Error parsing file: {e}", file=sys.stderr)
            sys.exit(1)

        process_combined_file(score, file_path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
