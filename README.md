# MergeDragons-Save-Editor

A savegame editor and APK injection tool for Merge Dragons.

## Overview

- **SaveGameEditor**: Python tool to analyze and edit Merge Dragons savegame databases
- **APKInjection**: Injects code into Merge Dragons APK to enable savegame export/import

## Features

### SaveGameEditor
- SQLite database analysis
- JSON mapping for data transformation
- Configurable data display

### APKInjection
- Automated Java compilation and DEX creation
- APK decompilation/recompilation
- Permission patching
- Code injection into UnityPlayerActivity
- Automatic APK signing

## Structure

```
MergeDragons-Save-Editor/
├── APKInjection/
│   ├── inject.py          # Main injection script
│   ├── Injector.java      # Java injector source
│   ├── tools/             # Android development tools
│   └── mergedragons.exe   # APK extraction tool
├── SaveGameEditor/
│   ├── editor.py          # Main editor script
│   ├── mapping.json       # Data mapping config
│   └── md_db.db          # Sample database
└── LICENSE
```

## Requirements

### SaveGameEditor
- Python 3.6+
- sqlite3, json (standard libraries)

### APKInjection
- Java 8+ JDK
- Python 3.6+
- Windows (for .exe/.bat files)

## Usage

### SaveGameEditor
```bash
cd SaveGameEditor
python editor.py md_db.db mapping.json
```

### APKInjection
```bash
cd APKInjection
python inject.py
```

**Process:** APK extraction → Java compilation → DEX creation → APK manipulation → Code injection → Signing

**Result:** `mergedragons_injected.apk` with savegame export/import functionality

## Injector Functionality

The injected code (`Injector.java`):
1. Shows toast notification on startup
2. Checks storage permissions
3. Exports savegame to `/sdcard/MergeDragons/md_db_[timestamp].db`
4. Imports from `/sdcard/MergeDragons/md_db_import.db` if present
5. Restarts app after import

## Mapping Configuration

`mapping.json` defines how internal data structures are displayed:

```json
{
  "file_map": {
    "_playerData": "Player Data",
    "_homeStats": "Camp Stats"
  },
  "data_map": {
    "Player Data": {
      "0": "Gems",
      "1": "Dragon Eggs"
    }
  }
}
```

## Important Notes

- For private use only
- Create backups before use
- Requires access to private app data
- Tested on Android 8+ (API 21+)

## License

MIT License - see [LICENSE](LICENSE) file.

## Disclaimer

Use at your own risk. Author is not responsible for data loss or damage.

## Contributing

Contributions welcome! Open issues or pull requests for improvements.
