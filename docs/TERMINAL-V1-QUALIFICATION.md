# Ryzova terminal v1 qualification

| Workflow | Evidence available | Remaining acceptance condition |
| --- | --- | --- |
| Select and run | PR #139 boots the amd64 guest, selects Linux, runs the HTTP fixture and checks the filtered response. | Run the three target binaries on one input in a single fresh guest terminal session. |
| Build and test | PR #137 builds the same checksum CLI and checks results on native Windows, Linux and macOS runners. | Select workflow and target with `ryz env trans`, then build and test from the guest project directory. |
| Windows source compatibility | PR #138 covers default-security directory creation and removal on simple relative paths. | Verify the supported subset through the guest build interface and diagnose an unsupported API. |
| Service control | PR #139 covers a threaded local HTTP fixture, output redirection and a failing launcher invocation. | Start and stop a separate service process and check its status from the terminal. |
| Developer tools | PR #140 packages the CLI and executes a clean extraction on each native runner. | Clone a project, restore dependencies, debug a failing test and package the fixed project from the guest. |
| Distribution | The Phase 5F qualify job downloads all three published ZIPs and checks their manifests, digests, binary formats and x86-64 machine identifiers. | Exercise missing SDK and wrong-architecture diagnostics on a clean guest installation. |

Terminal v1 acceptance requires all remaining guest conditions to pass on the release revision. Native package verification covers the three amd64 artifacts in the current workflow run.

## Single-source C project on the amd64 guest

Source `. /rc/lib/ryz-env` once in the guest rc shell. In a project directory containing an ANSI C `main.c`, run `ryz env native`, `ryz build`, and `ryz run`. The native build uses the guest's APE `pcc` and writes `build/native/app`. Edit the source and repeat both commands to run the new executable.

For a Windows workflow targeting macOS, use `ryz env trans windows macos`. Configure `ryzmaccc` with the name of a trusted compiler adapter that accepts a source pathname and output pathname and returns a failing status on error. Then `ryz build` produces `build/macos/app`. The integration test uses a loopback host adapter restricted to its generated source and verifies the returned executable on a macOS runner. An installed compatible Compact runtime and supported imports are required to run macOS programs in the guest.
