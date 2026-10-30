# Local toolkit setup and execution

Use the independently installed public toolkit. These commands describe the
external project; no bundled script or binary needs to be fetched from Agensi.

## Installation

Target: the public **v0.6.0** release.
Use an existing installation if suitable. If setup has been requested, install
into a new user-selected directory; do not reset or overwrite an existing repo.

```sh
git clone --branch v0.6.0 --depth 1 https://github.com/berglingtim/auto_paper_reading.git auto_paper_reading
cd auto_paper_reading
git describe --tags --exact-match
```

The reported tag should be `v0.6.0`. For an existing modified or
different version, inspect the difference or choose a separate pinned checkout;
do not silently substitute unverified code. If Git is unavailable, the same
version's source archive is available from its GitHub release page.

Use Python 3.10+ and Node.js. A Python virtual environment is recommended:

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
```

macOS/Linux shell:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci
```

In subsequent examples, `python` means the interpreter containing the installed
dependencies; substitute the venv executable explicitly if it is not activated.
Run all project commands with the toolkit root as the current directory.

The converter stages input, output, and its profile in the system temporary
directory using short names, then safely publishes the verified PDF into the
requested output directory. It therefore does not pass deep project paths to
Office. The host must permit local read/write access to its temporary directory.

Install [LibreOffice](https://www.libreoffice.org/download/download-libreoffice/)
with Writer and Math for DOC/DOCX input conversion and final PDF/page previews.
This is a separate free application. It is not provided by pip or the adapter.
The CLI detects common installations. If necessary, set `LIBREOFFICE_PATH` to
the actual `soffice.com` executable on Windows or `soffice` on macOS/Linux.
Use a process-local environment variable; no registry or file-association edits
are needed. Install the report's fonts through the user's normal setup process.

The release uses Times New Roman, SimSun, and SimHei. Font availability and
substitution affect layout. Real rendering has been checked on Windows;
macOS/Linux rendering is not yet validated for this project.

## Preflight

From the toolkit root, with the chosen Python interpreter:

```sh
python -c "import sys; sys.path.insert(0, 'src'); from auto_paper_reading import __version__; print(__version__)"
python -c "import fitz, docx, PIL, lxml; print('Python dependencies available')"
node --version
node -e "const {Document,Packer}=require('docx'); if(typeof Document!=='function'||typeof Packer.toBuffer!=='function') process.exit(1); console.log('docx dependency available')"
python run.py --help
```

The toolkit version should be `0.6.0`. Also check the configured LibreOffice
executable with `--version` before promising PDF previews. A working version
command does not replace an actual conversion and page review.

If required tools are unavailable, explain the missing capability and stop
only the dependent steps. PDF parsing and DOCX generation can run without
LibreOffice, but that is an incomplete visual-verification workflow.

## Run a report

The following uses an example input at `papers/paper.pdf` and an English output
root. Substitute the real user-selected paths and quote paths containing spaces.

```sh
python run.py "papers/paper.pdf" --stage prep --out "output/en" --language en
```

The CLI appends the input stem: the actual work directory is
`output/en/paper/`, containing `paper.json` and `figures/`.
Author the report at `output/en/paper/content.json`.
For Word input, substitute the actual `.doc` or `.docx` path; prep first
converts it using LibreOffice.

Use the external toolkit's `examples/en/content.json` and
`examples/zh/content.json` for valid JSON/block syntax. These are layout
fixtures, not research reports. Refer to `src/auto_paper_reading/docx_content.py`
for supported content fields. Read actual figure IDs, paths, and dimensions
from the prep output; do not invent them.

```sh
python run.py "papers/paper.pdf" --stage docx --out "output/en" --language en --verify
```

Use the exact DOCX path reported by the command as the argument to
`python tools/verify_math.py`. English filenames begin `Explanation_`;
Chinese filenames begin `讲解_`. The builder may add a suffix when a file is busy.
Do not select a different file merely because it has a similar name.
The matching PDF and page PNGs are in the work directory's `verify/` folder;
the DOCX and its `.math_audit.json` are in the work directory itself.

For Chinese, author Chinese content with `"language": "zh"` and use
`--out "output/zh" --language zh` in both stages. For bilingual output, repeat
with separate content files; changing a flag cannot translate a report.
Use a fresh output root when preserving earlier work is necessary.

## Rendering and failures

Use the default LibreOffice backend. WPS is optional only when explicitly
selected with `--pdf-backend wps`; never silently switch to it. Do not open an
office GUI or change security settings to work around a failed conversion.

The Python build injects editable OMML and runs the equation audit. Calling
`tools/build_docx.js` directly only produces an intermediate file.
When `--verify` fails, the DOCX can remain but the CLI returns a nonzero status.
Check the error and report the failure; old PDFs, PNGs, or audits are not
evidence for the failed attempt.

If the host blocks temporary-directory or converter access, report the actual
error and use the host's normal authorization flow if appropriate. Do not
change security settings or substitute old output for the failed attempt.

Scanned PDFs need separate OCR. Confirm a usable text layer before relying
on parsed text. Complex layouts can require manual figure recropping.
No cloud converter, paid office application, or separate LLM API key is required
by the toolkit; the host agent's own account and usage costs still apply.

## Dependency licensing

The project's original code and documentation are MIT licensed. That does not
relicense its dependencies or the papers it processes. In particular,
[PyMuPDF](https://pymupdf.readthedocs.io/en/latest/about.html) is offered under
AGPL/commercial terms. See the relevant upstream licenses when distributing
dependencies or offering a derived service.
