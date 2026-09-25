# Compliance documents

PAT Compliance reads the documents in these folders when you run, for example:

```bash
python -m perenic review app.py --industry healthcare --compliance-docs compliance_docs/healthcare
```

**The files here are starting points only.** The regulation files are short plain-English summaries of selected sections. They are **not** the official text and are not legal advice. Replace them with, or add alongside them:

- the official regulation text your organisation follows (PDFs work), and
- your organisation's own internal policies.

## Tips for good results

- Use Markdown headings (`#`, `##`) that name the rule, e.g. `## §164.312(b) Audit controls`. PAT Compliance cites these headings in its findings.
- PDFs are split into pages, so findings will cite `Page 12` and so on. Markdown gives more precise citations.
- Keep one topic per file. It makes searching faster and citations clearer.
