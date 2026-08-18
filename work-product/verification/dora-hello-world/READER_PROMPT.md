Read TUTORIAL_CONTRACT.md, VERSIONS.md, ASSET_GUIDE.md, and README.md.

Reproduce the supplied Dora Hello World example as a tutorial reader. This is
an execution and verification task, not a request to redesign the example.

First report:

1. the authoritative Dora CLI, Dora Python, and Python versions;
2. the single entry command and parameters;
3. expected generated files;
4. exact acceptance marker.

Then run exactly:

```powershell
./run.ps1 -Seconds 4
```

Do not edit source files. Do not search for or install a newer or older Dora
version. Do not replace the entry script or run installation commands outside
it. If either command fails, stop and report the sanitized error and the
contract it conflicts with.

On success, report only sanitized version lines, the listener output marker,
the observed acceptance marker, and changed or generated paths. Do not infer a
marker from its presence in `run.ps1`; it must appear in actual command output.
