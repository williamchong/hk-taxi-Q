"""Build-time geodata pipeline: HK government open data to game-ready assets.

Runs offline, never at run time — the game makes zero network calls (CLAUDE.md
hard rule 2). City specifics live in `config/cities/*.yaml`, never here.
"""

__version__ = "0.1.0"
