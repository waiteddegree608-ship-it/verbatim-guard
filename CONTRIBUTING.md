# Contributing

Use Python 3.10 or later and a virtual environment:

```sh
python -m venv .venv
# Activate the environment for your shell, then:
python -m pip install -e .
python -m unittest discover -s tests -v
```

Keep the core offline and free of runtime dependencies. Include a small synthetic
regression example for matching changes. Preserve original-source coordinates.
Any normalization that changes which quotes pass must remain explicit and documented.

Use issues for reproducible bugs and specific integration needs. Include the input,
expected result, actual result, Python version, and package version. Do not include
private source documents, API credentials, or copyrighted datasets you cannot share.

The current scope is literal evidence validation. PDF parsing, retrieval, and semantic
judgment belong in adapters or downstream applications with separately described behavior.
