# Architecture

## Module overview

```
src/neatxmp/
├── main.py         # GUI and user interaction
├── date_parser.py  # Parse dates from strings
├── xmp_writer.py   # Create and update XMP sidecar files
├── xmp_reader.py   # Read fields from XMP sidecar files
└── settings.py     # Persist user preferences
```

---

## `main.py` — GUI

Built with [Dear PyGui](https://github.com/hoffstadt/DearPyGui). The layout is a single primary window with:

- A folder selector (Browse button + label showing the current path)
- A Preview / Apply mode radio button
- Action buttons that trigger operations on the selected folder
- A scrollable log area (read-only `input_text`)

State is minimal: a single `_folder: str` global holds the current folder path. All actions read this and the mode toggle, then write results to the log.

The file dialog (`dpg.file_dialog`) is created hidden at startup. When Browse is clicked, `default_path` is set to the current folder before the dialog is shown, so it opens in the right place.

**Action flow for Apply Folder Name / Apply File Name:**

```
action button clicked
  └─ _current_folder()          resolve and validate folder
  └─ _media_files(folder)       list matching files
  └─ for each file:
       find_date_in_name(name)  parse date from folder or file name
       _apply_or_preview()      write XMP or log preview line
```

---

## `date_parser.py` — Date parsing

### `DateResult`

```python
tuple[int, Optional[int], Optional[int]]  # (year, month, day)
```

Month and day can be `None` for lower-precision matches (year-only or month+year).

### `format_xmp_date(parsed)`

Converts a `DateResult` to an XMP-compatible partial date string:

| Precision | Output |
|-----------|--------|
| Year only | `"1988"` |
| Month + year | `"1988-03"` |
| Full date | `"1988-03-25"` |

All three are valid per the XMP/ISO 8601 spec.

### `parse_date(name)` — full-match

Tries each parser in order, returning the first match:

1. `_named_month_year` — `"Nov 2018"`, `"2018-November"`
2. `_sep_two_parts` — `"11-2018"`, `"2018-11"`
3. `_sep_three_parts` — `"01-11-2018"`, `"2018-11-01"`
4. `_six_digits` — `"201811"` (YYYYMM) or `"112018"` (MMYYYY)
5. `_eight_digits` — `"20181101"` (YYYYMMDD) or `"01112018"` (DDMMYYYY)
6. `_day_named_month_year` — `"01-Nov-2018"`, `"Nov-01-2018"`
7. `_compact_named_month` — `"11Nov2018"`, `"Nov112018"`, `"2018Nov11"`
8. `_year_only` — `"1988"`

Each parser uses `re.fullmatch` so the whole string must match. Validation is centralised in `_valid(y, m, d)`, which checks year range (1900–2100), month range (1–12), and day range using `calendar.monthrange` (catches Feb 30, Apr 31, etc.).

Ambiguous three-part numeric dates default to **DD-MM-YYYY** (European convention).

For compact six-digit strings, YYYYMM is tried first (year range validates it); MMYYYY is the fallback. Same logic for eight-digit strings with YYYYMMDD vs DDMMYYYY.

### `find_date_in_name(name)` — substring search

Used for both folder names and file names, since either may contain a date embedded in longer text (e.g. `"25Mar1988 Ball"`, `"IMG_20181101_123456"`).

First tries `parse_date` on the full string. If that fails, tries in order:

1. Eight-digit runs not adjacent to other digits (catches `YYYYMMDD` in camera filenames)
2. `YYYY-MM-DD` / `YYYY_MM_DD` with separators
3. `YYYY-MM` / `YYYY_MM` not followed by another separator+digits
4. Compact named month patterns (`DDMonYYYY` etc.) as substrings
5. Named month + year anywhere in the string
6. Standalone four-digit year (last resort)

More specific patterns are tried before less specific ones to avoid a year-only match swamping a month+year match.

---

## `xmp_writer.py` — Writing sidecars

### Creating a new sidecar

Writes a hard-coded template string with the date substituted in:

```xml
<?xpacket begin="..." id="...">
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="NeatXMP">
 <rdf:RDF xmlns:rdf="...">
  <rdf:Description rdf:about=""
    xmlns:xmp="http://ns.adobe.com/xap/1.0/"
    xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"
    xmp:CreateDate="2018-11"
    photoshop:DateCreated="2018-11"/>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>
```

### Updating an existing sidecar

XMP files wrap their XML in `<?xpacket?>` processing instructions that sit *outside* the root element, making the file technically invalid XML. The update process works around this:

1. Split lines into header PI, body XML, and footer PI
2. Parse body XML with lxml
3. Find `rdf:Description` element
4. If the `xmp` or `photoshop` namespace is not already declared on the element, rebuild it with the namespaces added (lxml's `nsmap` is immutable after creation)
5. Set both date attributes
6. Serialise back to XML and reassemble with the original xpacket PIs

If parsing fails at any point (malformed XML, missing `rdf:Description`), the file is overwritten with a fresh template.

### Backups

Before any update, the existing `.xmp` file is copied to `.xmp_bak` via `shutil.copy2` (preserving timestamps). A subsequent update overwrites the previous backup.

### Fields written

| Field | Namespace |
|-------|-----------|
| `xmp:CreateDate` | `http://ns.adobe.com/xap/1.0/` |
| `photoshop:DateCreated` | `http://ns.adobe.com/photoshop/1.0/` |

---

## `xmp_reader.py` — Reading sidecars

Uses the same xpacket-stripping approach as the writer before parsing with lxml.

### `read_xmp_dates(xmp_path)`

Returns `{label: value}` for a fixed set of known date fields (used by the Scan table).

### `read_all_xmp_fields(xmp_path)`

Returns all fields as `[(label, value)]` pairs, for the Detailed Scan view:

- **Attributes** on `rdf:Description` are simple key/value pairs
- **Child elements** may be simple text or complex containers (`rdf:Seq`, `rdf:Bag`, `rdf:Alt`); list containers are joined with `"; "`
- Clark-notation keys (`{uri}local`) are mapped to conventional prefixes using a table of known namespaces; unknown namespaces are shown verbatim

---

## `settings.py` — Persistence

Reads and writes `~/.config/neatxmp/settings.json`. Currently stores one key:

```json
{ "last_folder": "/path/to/last/used/folder" }
```

The directory is created on first write. JSON decode errors are silently ignored (returns `{}`).
