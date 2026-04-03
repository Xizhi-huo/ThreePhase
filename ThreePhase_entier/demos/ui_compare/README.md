# UI Compare Demo

This folder contains two isolated demo UIs that present the same small screen in two different stacks:

- `pyqt_demo.py`: a single-file PyQt5 desktop UI
- `react_tauri_demo/`: a minimal React + Tauri desktop scaffold

Both demos show the same concepts:

- current mode
- current fault scene
- step progress
- a simple event log
- action buttons

## PyQt demo

Run:

```bash
python demos/ui_compare/pyqt_demo.py
```

## React + Tauri demo

This is only a minimal scaffold. It is intentionally isolated from the main project and does not reuse the current Python runtime.

Typical setup:

```bash
cd demos/ui_compare/react_tauri_demo
npm install
npm run tauri dev
```

## Quick comparison

| Item | PyQt | React + Tauri |
|---|---|---|
| Language | Python | TypeScript + Rust |
| UI style | Traditional desktop widgets | Modern web-style component UI |
| Reuse with current project | High | Low |
| Migration cost from current code | Lower | Much higher |
| Long-term UI flexibility | Medium | High |

This demo is meant to show the direction, not to replace the current app directly.
