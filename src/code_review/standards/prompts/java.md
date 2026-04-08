### Java
- Prioritize correctness and reliability: null-safety gaps, exception handling flaws, and resource leaks.
- Check thread-safety and state visibility in shared mutable objects.
- Flag API misuse that can silently fail (collections/streams, equals/hashCode contracts, Optional misuse).
- In Spring/Jakarta code, focus on validation, transaction boundaries, security annotations, and error mapping.
- Check for missing `@Transactional` rollback rules, improper lazy-loading outside of transactions, and missing `@Valid`/`@Validated` on controller inputs.
- Flag missing or overly broad exception handling in `@ControllerAdvice` and filter chains.
- `equals`/`hashCode` contract: flag classes that override `equals` without also overriding `hashCode` (or vice versa); objects will break when used in `HashMap`, `HashSet`, or any hash-based collection.
- Raw generic types: flag usage of raw types (e.g. `List` instead of `List<String>`) which bypass compile-time type safety and can cause `ClassCastException` at runtime.
- `instanceof` before cast: flag code that casts an object without first performing a null check — `null instanceof T` is always false so a cast on a null reference will throw `NullPointerException` even when the preceding `instanceof` passed on a non-null sibling reference.
