# Sine01 · AI PPT Workflow

Sine01 is a visual-first presentation workflow prototype. The product separates **content understanding, visual exploration, design locking, full-deck generation, future editable reconstruction, and QA** instead of forcing everything through one giant prompt.

## V0.1 scope

Current interactive path:

1. **Input** — paste a task brief and attach source files.
2. **Define** — adaptive questions only ask for missing high-impact constraints.
3. **Explore** — browse 8 genuinely different Styleboards. Each one contains cover/content/data mini slides.
4. **Select** — lock one design direction or mix layout, palette and imagery language.
5. **Generate** — preview a coherent 10-slide deck and regenerate individual slides or the whole variant.
6. **Deliver** — export project JSON or print the preview to PDF.

V0.1 intentionally does **not** pretend that editable PPTX reconstruction or AI file parsing is already complete. Those are explicit next-stage capabilities.

## Architecture

Long-term workflow:

```
Define · Explore · Select · Generate · Rebuild · Evaluate · Deliver
```

The implementation keeps the eventual AI provider behind a server boundary. Browser state never stores model API keys.

## Development

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

Production check:

```bash
npx tsc --noEmit
npm run build
```

A GitHub Actions workflow runs typecheck and build on `dev`, `main`, and pull requests to `main`.

## Branches

- `main` — stable baseline.
- `dev` — active development branch.

## Next milestone

Connect a real AI provider for Define / Explore / Generate, then implement the editable PPTX reconstruction router and visual evaluator loop.
