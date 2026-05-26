# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security issue in KHIS Toolkit — especially one involving credential handling, DHIS2 API authentication, or data exposure — please **do not open a public GitHub issue**.

Email `andyombogo@gmail.com` with:

1. A description of the vulnerability and its potential impact.
2. Steps to reproduce.
3. Any suggested mitigation if you have one.

I will acknowledge the report within 72 hours and aim to resolve confirmed issues within 14 days.

## Credential Handling Notes

- This repository intentionally embeds the **public DHIS2 demo credentials** (`demo_en` / `District1#` on `demos.dhis2.org/hmis_dev`). These are not secrets — they are published by the DHIS2 project for public testing.
- Real KHIS credentials must never be committed to this repository. The `.gitignore` excludes `.env` files. See `.env.example` for the expected configuration pattern.
- If you suspect that real Ministry of Health credentials have been accidentally committed, email immediately and I will revoke and rotate them.
