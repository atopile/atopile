# Investigate Test

Debug and fix a failing test.

## Test Runner

This project uses a custom test runner: `ato dev test`

Key flags:
- `--direct` - Run tests directly without isolation
- `-k <pattern>` - Filter tests by name pattern

```bash
ato dev test --direct -k $ARGUMENTS
```

For solver-related tests, enable detailed logging with these environment variables:
- `FBRK_LOG_PICK_SOLVE=y`
- `FBRK_LOG_FMT=y`
- `FBRK_SLOG=y`
