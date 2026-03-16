# NeatXMP

A desktop tool for stamping XMP sidecar files with dates parsed from folder or file names. Useful for organising photo and video archives where the date lives in the folder or filename but not in the metadata.

I made this tool for myself, to help with folders full of pictures that I scanned. I tend to use date strings in either the file names or folder names, and this tool will apply the date into the XMP sidecar so that photo tools recognize those dates.

**Lightly tested, still a work in progress.**

## AI Disclosure

This tool was created primarily by interacting with [Claude Code](https://claude.ai). I am code reviewing and testing in various degrees as I proceed. Use at your own risk.

## License

## What it does

NeatXMP creates or updates `.xmp` sidecar files alongside your media files, writing the date into the `xmp:CreateDate` and `photoshop:DateCreated` fields. It never touches the media files themselves.

**Supported media types:** `.jpg` `.jpeg` `.png` `.heic` `.mp4` `.mov`

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo>
cd NeatXMP
uv sync
```

## Running

```bash
uv run neatxmp
```

## Usage

### 1. Select a folder

Click **Browse…** to choose a folder. The app works on one folder at a time and remembers the last folder you used between sessions.

### 2. Choose a mode

- **Preview (dry run)** — shows exactly what would happen without writing any files
- **Apply (write files)** — writes changes to disk

### 3. Pick an action

| Button | What it does |
|--------|-------------|
| **Scan** | Shows a table of all media files with their filesystem modified date and any XMP dates already present |
| **Detailed Scan** | Shows every field found in each file's XMP sidecar |
| **Apply Folder Name as Date** | Parses a date from the folder name and writes it to all media files in the folder |
| **Apply File Name as Date** | Parses a date from each individual file's name and writes it to that file |
| **Clear Log** | Clears the log area |

Always run **Preview** first to confirm the dates look right, then switch to **Apply**.

## Supported date formats

The parser handles a wide range of formats, with or without separators, and both standalone and embedded in longer names (e.g. `"25Mar1988 Plumbers Ball"` or `"IMG_20181101_123456"`).

| Example | Parsed as |
|---------|-----------|
| `Nov 2018` · `November 2018` · `2018 Nov` | 2018-11 |
| `11-2018` · `2018-11` · `112018` · `201811` | 2018-11 |
| `01-11-2018` · `2018-11-01` · `01112018` · `20181101` | 2018-11-01 |
| `01-Nov-2018` · `Nov-01-2018` · `01 November 2018` | 2018-11-01 |
| `11Nov2018` · `Nov112018` · `2018Nov11` | 2018-11-11 |
| `1988` · `foo-1988` | 1988 |

Ambiguous three-part numeric dates (e.g. `05-03-2018`) are interpreted as DD-MM-YYYY.

## XMP fields written

Both fields are set to the same value on every create or update:

- `xmp:CreateDate`
- `photoshop:DateCreated`

Date precision matches what was parsed: `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`.

## Backups

Before modifying an existing sidecar, the original is saved as `<filename>.xmp_bak`. A subsequent update overwrites the previous backup, keeping one level of history.

## Running tests

```bash
uv run pytest
```
