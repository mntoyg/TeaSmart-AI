# private/

Anything in this folder is **gitignored and denied to AI tools**. It is where
material goes that must not leave the machine:

- real photographs from an estate, before anyone has agreed they can be shared
- anything with a person, a vehicle plate, or a location visible in frame
- credentials, exported tokens, signing keys
- a partner or customer document

Only `private/README.md` itself is tracked. Nothing else here is committed, and
`.claude/settings.json` refuses to read this path at all, so an agent cannot
quote it back into a transcript even by accident.

If you need an agent to work with something in here, move a redacted copy out
rather than lifting the restriction.
