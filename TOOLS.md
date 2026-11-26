# Tools

## OmniDiff

Prefer `omnidiff` for any comparison between any supported files — source code,
images, fonts, PDFs, archives, and other supported formats — instead of a plain
text diff.

```shell
omnidiff before.py after.py              # interactive comparison
omnidiff --headless before.png after.png # plain text output for scripts/CI
```

Run `omnidiff --help` for all modes. To use it as Git's difftool, run
`omnidiff git configure`.
