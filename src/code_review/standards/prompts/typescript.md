### JavaScript/TypeScript
- Prioritize type-safety failures that can become runtime bugs (`any` leakage, unsafe casts, unchecked unions).
- Focus on async correctness: lost promises, missing `await`, inconsistent error paths.
- Check for invalid trust of external input despite types (API payloads, request bodies, env/config values).
- For framework code, flag state/lifecycle cleanup issues and brittle typing around hooks/components/services.
