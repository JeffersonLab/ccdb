# CLI modernization: framework options, interactive mode, theming

Status: analysis / decision document, 2026-07. No implementation yet.
Companion: [cli-command-coherence.md](cli-command-coherence.md) (what the
command surface should look like). This note answers: what framework (if any)
to move to, what a full click switch would take — especially interactive
mode — and how to finally do colors correctly.

## 1. What the CLI actually is today

Understanding the port cost starts from what exists:

- **Per-command parsing is already argparse.** Every command in
  `ccdb/cmd/commands/` builds a `UtilityArgumentParser` — a 10-line
  `argparse.ArgumentParser` subclass that raises instead of exiting. This is
  the single most important fact in this note: the parsing layer needs no
  rescue, only the plumbing around it.
- **Hand-rolled pieces** (in `cli_manager.py` + `ccdb/__init__.py`):
  - global-flag parsing (`-c`, `-u`, `-i`, `-r`, `-v`, `--version`,
    `--debug`, `--no-color`, ...) as manual `sys.argv` scans in two places;
  - command discovery via `pkgutil` import + `CliCommandBase.__subclasses__()`;
  - dispatch (`process_command`) with lazy DB connection, an
    exception-handling mode (throw/silent/auto), and a string-alias mechanism
    (`dump` returns `"cat --no-borders ..."` which is re-dispatched);
  - `> file` output redirection and `!shell` escape inside the command line;
  - a readline REPL (`ccdb -i`): history file, tab-completion of DB paths,
    prompt showing `CliContext.current_path`.
- **Shared state**: `CliContext` (current_path, current_run,
  current_variation, user_name, connection string, theme) — mutated by `cd`,
  `run`, `var`, `user`, read by everything else. This is the interactive-mode
  state that must survive any port.
- **Exit-code contract** (fixed 2026-07): command returns `None`/`False` →
  exit 1, anything else → exit 0; enforced by CI (cli-smoke "Exit code
  contract" step).

## 2. Framework survey

Priorities, per Dmitry: **(a)** leave code close to what it is now but be
modern; **(b)** interactive mode matters; **(c)** autocomplete does NOT —
buggy or absent completion is acceptable and must not drive the choice.

### Option A — stdlib argparse, formalized (no framework)

Keep the command classes and the REPL; replace only the hand-rolled parts:
one top-level `argparse` parser for global flags with subparsers wired from
each command's existing `UtilityArgumentParser`. Delete both manual
`sys.argv` scan loops.

- **Code distance: smallest possible.** Commands are untouched; only
  `cli_manager.process()` and `init_ccdb_console()` shrink.
- **Interactive: solved by definition** — the current readline loop stays and
  keeps dispatching into the same registry it uses today.
- **Modern-ness**: stdlib, maintained forever, zero new dependencies. What it
  lacks: nothing ccdb needs except generated shell completion (explicitly
  deprioritized) and `--help` polish (argparse's is fine).

### Option B — cmd2 (interactive-first framework)

[cmd2](https://github.com/python-cmd2/cmd2) is purpose-built for exactly
ccdb's shape: an interactive shell that also runs one-shot commands.

- **Code distance: moderate, and unusually good reuse.** cmd2 commands are
  `do_<name>` methods decorated `@cmd2.with_argparser(parser)` — ccdb's
  existing `UtilityArgumentParser` instances plug in nearly verbatim.
  Command classes become methods on `CommandSet` classes (cmd2's plugin
  mechanism), so the one-file-per-command layout survives.
- **Interactive: this is cmd2's whole reason to exist.** History,
  `help`, startup scripts — and notably **native `> file` redirection and
  `!shell` escapes**, meaning two chunks of `cli_manager.py` get deleted
  rather than ported. Persistent state lives on the app object (drop-in home
  for `CliContext`).
- **Modern-ness**: actively maintained, argparse-native, used widely for
  operator shells. Its tab-completion is also better than ccdb's readline
  code, but that's a bonus, not a criterion.

### Option C — click

- **Code distance: largest.** Every command class must be rewritten as a
  decorated function; every `UtilityArgumentParser` re-expressed as
  `@click.option/@click.argument` decorators (argparse does not transplant).
  The dispatcher, global flags and help all come free after that rewrite.
- **Interactive: click has no REPL.** See section 3 — it's buildable but is
  extra work on top of the biggest rewrite.
- **Modern-ness**: the ecosystem default, excellent docs; and **rcdb already
  uses it** (`rcdb.cli.app:rcdb_cli`), which is the one real argument for
  click: two JLab tools converging on identical CLI infrastructure.

### Option D — typer

Type-hint-driven layer over click: commands are plain typed functions,
even less boilerplate than click once rewritten. Same total rewrite of the
parsing layer, same missing REPL, adds a second dependency on top of click.
Attractive greenfield; weakest "leave code close" score here.

### Option E — cleo (poetry's CLI library)

Class-per-command with a `handle()` method — structurally the nearest match
to `CliCommandBase` — plus built-in output styling tags. But: its own
signature DSL replaces argparse (rewrite of all parsers), no true REPL
(its "interactive" means prompting for missing inputs, not a shell), and it
is maintained primarily as poetry's internal library with thin docs.
Structure fits; everything else is a downgrade for ccdb.

### Option F — fire

Auto-generates CLIs from objects. Magic dispatch, weak help control, no
curated UX, "interactive" drops into a Python REPL — wrong tool for a
curated operator CLI. Rejected.

### Recommendation matrix

| | Code stays close | Interactive mode | Modern / maintained | Notes |
|---|---|---|---|---|
| **A: argparse formalized** | ★★★ | ★★★ (keep own loop) | ★★★ (stdlib) | least work, no deps |
| **B: cmd2** | ★★☆ | ★★★ (native, deletes code) | ★★★ | parsers reused via with_argparser |
| **C: click** | ★☆☆ | ★☆☆ (build it, §3) | ★★★ | rcdb parity is the one draw |
| D: typer | ★☆☆ | ★☆☆ | ★★★ | greenfield tool |
| E: cleo | ★★☆ (structure) | ★☆☆ | ★★☆ | parser DSL rewrite, thin docs |
| F: fire | ★★☆ | ✗ | ★★☆ | wrong fit, rejected |

**Recommendation:** given the stated priorities, **Option A now, Option B if
the shell deserves further investment; click only if rcdb parity is declared
a goal in itself.** A is a cleanup, not a port — it can land in days and
nothing about it blocks a later move to cmd2 or click. B is the only
framework that makes the interactive mode *better* while deleting hand-rolled
code (redirection, shell escape, history). C/D are justified solely by
ecosystem-uniformity arguments, at the price of rewriting the one layer
(argparse commands) that already works.

## 3. The click interactive-mode question, answered anyway

Since the question was asked directly: what would interactive mode cost under
a full click switch?

Click builds a command *tree* invoked once per process; it has no shell. The
options:

1. **click-repl** — a small plugin that walks the click tree inside a
   prompt_toolkit loop. Pros: ~free. Cons: barely maintained, shallow
   handling of errors/state, and ccdb's specials (`> file` redirect, `!`
   escape, path-prompt) still need custom code around it. Not recommended for
   a tool with ccdb's shell traffic.
2. **Custom loop over the click tree** (the realistic choice): read a line,
   `shlex.split`, call `cli.main(args, standalone_mode=False, obj=state)`.
   `standalone_mode=False` stops click from calling `sys.exit`; a persistent
   `obj` (click's `ctx.obj`) carries the `CliContext` equivalent across
   invocations, which is how current_path/variation/run survive between
   commands. Roughly 150–250 lines to reach parity: prompt from
   `state.current_path`, readline history, re-implement `>` redirection and
   `!` escape, map `ClickException`/usage errors to the silent/throw modes.
3. **prompt_toolkit directly** — same as 2 with a nicer line editor
   (multi-line, colored prompt, sane completion later). Adds a dependency and
   some code; reasonable upgrade *after* 2 works.
4. **cmd2 as the shell around click commands** — running two frameworks'
   dispatch models in one binary; the impedance mismatch (cmd2 wants
   argparse, click wants decorators) makes this the worst of both. Rejected.

The stateful commands (`cd`, `pwd`, `run`, `var`, `user`) become operations
on `ctx.obj` and are registered only with the shell's command set, fixing the
"shell state leaks into one-shot mode" incoherence documented in
[cli-command-coherence.md](cli-command-coherence.md).

Tab-completion of DB paths under click would be custom work in every variant
— explicitly out of scope per the stated priorities.

## 4. Theming: the actual goal is colors on / colors off

The current layer — `NoColorTheme` / `ColoredTheme` string constants
concatenated into `print()` calls, swapped manually on `--no-color` and on
`>` redirect — was never implemented correctly: no TTY detection, no
`NO_COLOR`, piping `ccdb ls | grep` emits escape codes, and every command
hand-assembles its styling.

The good news: "use colors or not, correctly" is a completely solved problem
in libraries, and it is **independent of the framework choice** — this can
ship first under any of A/B/C.

- **rich** (already a ccdb dependency): `Console` does TTY detection,
  `NO_COLOR`/`FORCE_COLOR`, and strips styles automatically when output is
  redirected. `--no-color` maps to `Console(no_color=True)`. A semantic
  `rich.theme.Theme` replaces the constants:

  ```python
  THEME = Theme({"dir": "bold blue", "ok": "bold green", "fail": "bold red",
                 "accent": "bold blue", "type": "cyan", "title": "bold"})
  console = Console(theme=THEME, no_color=no_color)   # one switch, one place
  console.print(f"[dir]{directory.name}[/dir]")
  ```

  The entire on/off question collapses into constructing one object. The
  `>`-redirect theme-swap dance in `cli_manager` gets deleted — rich already
  does the right thing for non-TTY targets. Tables (`ls`, `vers`, `help`)
  can later use `rich.table` instead of `%-10s` padding.
- **click.style / click.echo** — handles redirect stripping, but ties
  styling to click (undesirable if A/B wins) and offers raw colors, not a
  theme with semantic names.
- **blessed** — terminal-capability toolkit; lower-level than needed, we'd
  rebuild the theme/on-off logic ourselves.
- **colorama** — maintenance-mode Windows ANSI shim; ccdb already removed
  it deliberately. **termcolor** — trivial wrappers, no TTY/`NO_COLOR`
  logic. Both rejected.

**rich wins on every axis** and is already installed. Migration is
per-command and behavior-preserving (the 33 CLI integration tests capture
stdout): replace `theme.X + text + theme.Reset` with `console.print`
markup; delete `themes.py` when the last command converts.

## 5. Sequencing, effort, and what ships incrementally

Phases (each independently shippable; estimates assume familiarity with the
code, single developer):

| Phase | What | Effort | Ships incrementally? |
|---|---|---|---|
| 0 (done) | exit-code contract + CI enforcement; rich generates the ANSI constants | — | done |
| 1 | rich Console/Theme color on/off; delete theme plumbing command-by-command | 2–4 days | yes — per command |
| 2 | Option A: top-level argparse for global flags + subparser wiring; delete hand parse loops | 2–3 days | mostly — one cutover of global-flag behavior |
| 3a | Option B (cmd2): CommandSets, native redirect/history, delete REPL code | 1.5–2 weeks | shell cutover is hard; one-shot can move first |
| 3b | Option C (click): rewrite all ~23 commands as decorated functions + custom REPL loop (§3.2) | 3–4 weeks | command surface converts as a whole; REPL after |
| 4 | command-coherence renames (add/rm nouns) with old spellings as deprecated aliases | 3–5 days on top of 3 | aliases make it soft |

Hard-cutover risks concentrate in phase 2/3 edge behaviors: `#comment`
arguments (`mkdir /a #comment`), `> file` redirection, `!` escapes, flag
oddities (`-c` accepted before *or* after the command), and the alias
mechanism (`dump`→`cat`, `ls`→`vers`). The CLI integration tests plus the
cli-smoke workflow are the regression net; keep `process_command_line()` as
the test-facing API whatever happens beneath it.

Deprecated-alias strategy (phase 4): whichever framework hosts the new
spellings, old ones (`mktbl`, `mkvar`, `dump`, ...) stay registered for one
major version, print a single deprecation line to stderr, and forward —
trivial in all of A/B/C.

## Bottom line

- The port question is smaller than it looks because the parsing layer is
  already argparse; the REPL question is smaller than it looks because the
  loop already exists and works.
- **Do phase 1 (rich colors) and phase 2 (argparse formalization) regardless
  of any framework decision** — they are cheap, modern, and reversible.
- Adopt **cmd2** if/when the interactive shell justifies a framework: it is
  the only option where interactive mode gets *better* while code gets
  *deleted*, and ccdb's parsers carry over.
- A **full click switch is ~3–4 weeks** with the REPL rebuilt as a custom
  loop over the click tree — technically fine, but it rewrites the healthiest
  layer of the current CLI and its only unique payoff is rcdb consistency.
