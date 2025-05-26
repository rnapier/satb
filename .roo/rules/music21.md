# Music21 library

Prefer the `.recurse()` iterator to `.flatten()`.

## Example of filtering by voice

```python
def strip_to_single_voice(s: stream.Score, voice_number: int) -> stream.Score:
    result = s.deepcopy()  # Preserve full structure
    for part in result.parts:
        for meas in part.getElementsByClass(stream.Measure):
            voices = meas.getElementsByClass(voice.Voice)
            for v in voices:
                if v.id != str(voice_number):
                    meas.remove(v)
    return result
```
