### JavaScript
- Focus on runtime safety: flag null/undefined access, async error handling, and unhandled promise flows.
- Check for race conditions and stale-state bugs in async UI/server logic.
- Flag injection risks: `eval`, dynamic code execution, unsafe template/HTML handling (XSS), and unsafe command/SQL construction.
- For React code, prioritize lifecycle/cleanup issues (missing cleanup in `useEffect`, stale closures, ref misuse), state mutation bugs, and missing key props.
- For Vue code, check for state mutation outside of mutations/actions (if using Vuex), lifecycle hooks misuse, and missing prop validation.
- For Node.js / Express code, focus on request validation, error propagation, missing rate limiting, and unsafe path construction.
- Prototype pollution: flag `Object.assign({}, userInput)` or spread (`{ ...userInput }`) onto objects used as prototypal ancestors, and direct property writes on `Object.prototype`. Also flag `__proto__` or `constructor.prototype` accessed from user-controlled input, which allows attackers to inject properties onto all objects in the process.
- `eval` / `Function()` with external input: flag `eval(userStr)`, `new Function(userStr)`, and `setTimeout(userStr, ...)` — these execute arbitrary code and are a critical injection vector.
