# Starforge Lab resources

Runtime payloads in this directory are generated locally by:

```bash
./scripts/vendor_python.sh
```

The generated `Python.xcframework`, `bin/python3`, `engine/`, `pysite/`, and wheel
downloads are intentionally ignored by git. The app bundle copies them from here
when present.
