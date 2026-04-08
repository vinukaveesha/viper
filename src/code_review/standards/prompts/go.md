### Go
- Emphasize explicit error handling and context-rich wrapping where failures matter.
- Check `defer` and resource lifecycle correctness (files, bodies, locks), including `defer` in loops.
- Review concurrency hazards: goroutine leaks, shared-state races, deadlocks, and context cancellation misuse.
- Flag API contract issues around nil/zero values and exported behavior, not cosmetic gofmt concerns.
- For HTTP handlers, check that errors returned by `http.ResponseWriter` writes are handled, and that panics are recovered at the handler boundary.
- For database code, check for missing transaction rollback on error, unclosed rows/statements, and SQL injection via string concatenation.
- `context.Context` propagation: flag functions that accept a `context.Context` parameter but ignore it (passing `context.Background()` or `context.TODO()` internally instead), breaking cancellation and deadline propagation to callers.
- HTTP response body leaks: flag `http.Get` / `http.Do` calls where `resp.Body` is not closed via `defer resp.Body.Close()` on all code paths, including error returns where `resp` may be non-nil.
- `defer` inside loops: flag `defer` calls placed inside a `for` loop body — defers accumulate until the surrounding function returns, not the loop iteration, causing resource leaks and unpredictable cleanup order.
