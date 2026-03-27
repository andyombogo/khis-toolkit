# Publishing KHIS Toolkit To PyPI

## 1. Install publishing tools

```bash
pip install build twine
```

## 2. Build the distribution files

```bash
python -m build
```

This creates source and wheel distributions in `dist/`.

## 3. Validate the package metadata

```bash
twine check dist/*
```

## 4. Upload to PyPI

```bash
twine upload dist/*
```

You will need a PyPI API token. The recommended approach is to create a token on PyPI and use it instead of a password.

## 5. Verify the release

- Confirm the project page renders correctly on PyPI
- Test installation with `pip install khis-toolkit`
- Open the README on PyPI and confirm badges and links still work
- Tag the release in GitHub and update `CHANGELOG.md` for the next version
