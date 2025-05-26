ALWAYS access Python via `uv`. Never access `python` directly.

This is a personal project, intended just for me. Do not make it any more complicated than it needs to be.

Performance is not a major concern. Do not add performance tests or add extra features for performance.

Do not add configuration options unless specifically requested.

Do not add fallbacks to try to recover from bad data. If data is not in the expected format, raise a clear error.

Do not add any complexity that is not specifically requested.

Ask your user for help whenever you have trouble.

Do not hack things or build workarounds. If you cannot find a clear, obvious approach to a problem, ask your user for help.

Use the public API of your dependencies. Do not rely on internal implementation details. If you are not certain of the API and cannot find the documentation, ask your user for help.