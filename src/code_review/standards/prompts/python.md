### Python
- Flag mutable default args, implicit `None` handling bugs, and exception swallowing.
- Verify resource safety: context managers, file/socket/db cleanup, and transaction handling.
- Check async correctness: blocking calls inside async paths, missed `await`, cancellation safety.
- Call out dangerous deserialization/eval/subprocess usage and unsafe string-built SQL/shell commands.
- Prefer type-hint clarity when it prevents bugs (public APIs, complex data flow), not as style-only noise.
