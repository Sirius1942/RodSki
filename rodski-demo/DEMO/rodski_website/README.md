# RodSki Website Acceptance

This module verifies the local `rodski-website` Next.js site with RodSki UI
acceptance cases.

## Scope

- Root route redirects/responds as `/landing`.
- Landing page exposes working links to current documentation routes.
- v8 documentation home and core pages respond.
- v7 historical documentation and migration links respond.
- `/llms/v8/*.md` text routes serve content from `content/v8/*.mdx`.
- Missing documentation routes return 404.

## Local Setup

The cases use `data/globalvalue.xml`:

```xml
<var name="BASE_URL" value="http://localhost:3001"/>
```

Start the website dev server before running these cases:

```bash
cd rodski-website
npm run dev
```

If your local Next.js server uses a different port, update
`data/globalvalue.xml` before executing the cases.

Rebuild test data after changing expectations:

```bash
python3 rodski-demo/DEMO/rodski_website/data/build_data.py
```

Run a dry check:

```bash
rodski data validate rodski-demo/DEMO/rodski_website
rodski run rodski-demo/DEMO/rodski_website/case --dry-run --output-format json
```
