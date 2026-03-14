### Go
- Emphasize explicit error handling and context-rich wrapping where failures matter.
- Check `defer` and resource lifecycle correctness (files, bodies, locks), including `defer` in loops.
- Review concurrency hazards: goroutine leaks, shared-state races, deadlocks, and context cancellation misuse.
- Flag API contract issues around nil/zero values and exported behavior, not cosmetic gofmt concerns.
