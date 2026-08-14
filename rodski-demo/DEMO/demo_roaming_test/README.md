# demo_roaming_test

Self-contained RodSki roaming acceptance demo. It uses a local static HTML page,
Playwright, deterministic SQLite data, and the built-in rule-based roaming
engine. It does not use the public network, an LLM, or an external service.

The source tree contains the six standard module directories:

```text
demo_roaming_test/
|-- case/
|-- model/
|-- fun/
|-- data/
|-- plan/
`-- result/
```

`knowledge/` is intentionally absent from the source layout. RodSki creates
`knowledge/test_map.json` only after a successful roaming action.

## Acceptance

From the repository root, run with the project's Python 3.12 interpreter:

```bash
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 \
  rodski-demo/DEMO/demo_roaming_test/run_demo.py
```

The launcher starts a static HTTP server on `127.0.0.1` with an ephemeral port,
creates `data/data.sqlite`, and executes these real CLI workflows:

```bash
rodski run rodski-demo/DEMO/demo_roaming_test --roam \
  --headless --output-format json

rodski roam --case RT001 rodski-demo/DEMO/demo_roaming_test \
  --headless --output-format json
```

For both workflows it asserts:

- the base case passes after typing DataID `D001`;
- roaming executes the alternative DataID `D002` through the normal `type`
  keyword and Playwright driver;
- JSON contains `roam_summary.variants_tried > 0`;
- the summary reports a successful Test Map write;
- `knowledge/test_map.json` exists and contains an edge whose action uses
  `data="D002"`.

The final JSON printed by `run_demo.py` contains the evidence for both entry
points. Runtime SQLite and temporary configuration files are removed when the
launcher exits. Generated `result/` and `knowledge/` artifacts can be removed
between runs; the launcher also resets them at the start of its next run.
