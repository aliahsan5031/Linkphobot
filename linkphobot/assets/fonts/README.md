# Bundled fonts

Shipped with the app so images look the same on every machine (Hugging Face
Spaces has almost no system fonts).

- **Inter** (Regular, Medium, SemiBold, Bold), by Rasmus Andersson. SIL Open Font License 1.1.
- **Poppins** Bold, by Indian Type Foundry. SIL Open Font License 1.1.

Both licences allow bundling and redistribution (https://openfontlicense.org).

The `.b64` files are the fonts subset to Latin, Greek and Cyrillic, compressed and
base64-encoded, because Hugging Face rejects binary files in a plain git push.
Rebuild them from the original fonts with `python scripts/pack_fonts.py <font files>`.
