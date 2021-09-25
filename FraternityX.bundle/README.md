# Kink.bundle

## Description

Plex metadata agent for fetching episodic metadata from Kink.

This uses metadata and posters that are available from the site (free).

By default, this matcher expects files to be named like:
* `Kink/{title}.ext`

## Installation

Copy CockPorn.bundle and RawFuckClub.bundle to the Plex plugins path. See
[How do I find the Plug-Ins folder?][1] for more information.

## Known Issues

- Limited ability to match titles with special characters in the name.
- Unable to get metadata for bonus material from other sites.
- Autoupdate may cause issues as it may cause a full metadata refresh when a
new file is added.

[1]: https://support.plex.tv/hc/en-us/articles/201106098-How-do-I-find-the-Plug-Ins-folder-
