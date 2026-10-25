# Stage07: common ESMF mesh-read segmentation fault; inspect mesh and stack

**Later Stage07 output received:** mesh headers are readable; the declared dust grid has1,036,800elements and a15.8MiB offset-array estimate. Login soft stack is8MiB; actual failed-task limits remain unmeasured. [Stage08 defines a single FI-Hyy task-side stack256 retry](stage08_FI_Hyy_stack256_AD5_pilot_20261025.md). This is a controlled hypothesis test, not a completed repair.

## Evidence from the operator's Stage06 output

The uploaded `Pasted text(20261025-085531).txt` reports four identical startup failure locations:

- FI-Hyy4728102, FR-Hes4728104, CH-Fru4728106 and IT-MBo4728108 all failed after9–10seconds wall time on red6083.
- Their executable tasks exited with signal11, with backtraces in `get_centerCoords_from_ESMFMesh_file()` at local `ESMCI_ESMFMesh_Util.C:1028`, called by `ESMCI_mesh_create_from_ESMFMesh_file()`.
- Land logs printed `spinup_state=2` and accelerated AD mode before termination.
- Four archive jobs4728103/05/07/09 are pending with `DependencyNeverSatisfied`.
- The ETALAKE line is explicitly a WARNING in the supplied excerpts. It is not the reported fatal backtrace, and these excerpts do not establish it as the cause.

Existing full Stage06 report: `/home/ly3n24/Batch02_10_AD5_failure_diagnosis_um3gr1l2/failure_diagnosis.json` (and adjacent text report). The failure is localized to common ESMF mesh initialization. The underlying trigger is still unverified: a code location and signal do not alone distinguish a stack-limit issue, invalid mesh metadata/arguments or another library defect. A common node does not establish a node fault.

## Why inspect stack and the actual mesh

The [upstream ESMF v8.8.1 source](https://github.com/esmf-org/esmf/blob/v8.8.1/src/Infrastructure/Mesh/src/ESMCI_ESMFMesh_Util.C#L1023) allocates a variable-size automatic `cc_offsets[num_elems*coordDim]` array and writes its entries at the reported location. This makes stack capacity worth checking, but does **not** prove stack overflow. The local source is also inspected because the upstream version label is not proof of identical local build bytes.

[Stage07](../scripts/07_inspect_ESMF_mesh_stack_readonly.py) reads declared mesh paths, mesh header dimensions and small coordinate arrays; prints an explicitly labelled allocation-size estimate; inspects stack-related batch/environment lines and the local ESMF source; and compares the four Batch02 cases with their original source cases plus the previously successful FI-Sod/FR-Fon Batch01 references.

```bash
(
  set -euo pipefail
  SCRIPT="$HOME/Batch02_10_stage07.py"
  curl -fLsS --retry 3 \
    "https://raw.githubusercontent.com/lyanyeung/Non-Competition-CLM-experiment/6d9f9843d434f07b60538063c0750922eceb1410/examples/Batch02_10/scripts/07_inspect_ESMF_mesh_stack_readonly.py" \
    -o "$SCRIPT"
  echo "42fcd8447b71db484cd984848bf5b74f10c721af0fd45a9677f8f92542457028  $SCRIPT" | sha256sum -c -
  python3 -B "$SCRIPT" self-test
  python3 -B "$SCRIPT" inspect
)
```

The current Python/login stack limit is explicitly labelled **not the failed compute tasks' measured limit**. The script does not set ulimit, alter meshes/forcing/PFT/soil, cancel archives or submit another pilot. No meteorology or large mesh arrays are scanned. It reuses the saved Stage06 log tails rather than repeating the general scheduler audit.

A new HOME directory contains `mesh_stack_inspection.json`. Console output includes `LOCAL ESMF SOURCE AT CRASH`, per-case relevant mesh/stack declarations and `DECLARED MESH HEADERS`. Missing/unreadable meshes are explicit evidence gaps. Model run retries remain pending until the targeted evidence supports a repair.

Validation: standard-Python self-test and a four-case/source/reference fixture passed, including declared-mesh-only extraction, missing-mesh reporting, source-byte preservation and report generation. Actual mesh-header inspection requires the existing IRIDIS netCDF4 environment; this local environment has no netCDF4 and no HPC model files.
