# Frequently Asked Questions

## Installation

### Installing via pip or conda gives an older version instead of the latest

**Symptom:** Running `pip install movinglines` or `conda install samuelleblanc::movinglines` installs an older version (e.g. v1.64) when a newer version (e.g. v1.66) is expected. Starting the software with `ml` confirms the old version number.

**Cause:** The package index (PyPI or the conda channel) may cache or default to an older build. This can be compounded if both a pip and a conda install of `movinglines` exist in the same environment — pip-installed packages shadow conda ones.

**Solution:**

First, try forcing the specific version via conda:
```
conda install samuelleblanc::movinglines==1.66
```
or via pip:
```
pip install --force-reinstall movinglines==1.66
```

> **Note:** There were dependency changes between v1.64 and v1.65/v1.66 which may cause conflicts in environments originally created for v1.64.

If the forced install appears to succeed but the software still reports the old version on restart, a pip-installed copy is likely shadowing the conda package. Fix this by removing it first:

1. Remove any pip-installed copy:
    ```
    pip uninstall movinglines
    ```
2. Confirm the uninstall completed (the command should report that `movinglines` is not installed):
    ```
    pip uninstall movinglines
    ```
3. Now install the desired version via conda:
    ```
    conda install samuelleblanc::movinglines==1.66
    ```

**Cleanest fix — recreate the environment from scratch:**

If version conflicts persist, removing and recreating the conda environment ensures a clean slate:
```
conda deactivate
conda remove -n ml --all
conda create -n ml python=3.9
conda activate ml
mamba install -c samuelleblanc movinglines
```
*(Replace `mamba` with `conda` if mamba is not available.)*

After a clean environment creation, the default install should resolve to the latest published version without needing to force a specific version number.

---

### conda install hangs or spins indefinitely ("Solving environment" never completes)

**Symptom:** Running `conda install` or `mamba install` gets stuck — the terminal shows a spinning indicator or prints repeated `filter_group` / pruning debug messages for 30+ minutes and never finishes. This is most common on macOS with the default Anaconda installation.

**Cause:** The default conda dependency solver (classic) is very slow and can appear to hang on large package sets. A full cache from previous failed install attempts can make this worse. `mamba` may also loop if it cannot find the `movinglines` channel without explicit channel configuration.

**Solution:**

*Step 1 — Clean the conda cache* (especially if you have made several previous install attempts):
```
conda clean --index-cache --tarballs --packages --yes
```

*Step 2 — Switch to the faster `libmamba` solver:*
```
conda install -n base -c conda-forge --override-channels conda-libmamba-solver --yes
conda config --set solver libmamba
```
> **Note:** Installing `conda-libmamba-solver` into the base environment may itself be slow the first time. If it hangs again at "Solving environment", wait — 30 minutes is not unusual on the first run. Progress messages like `examining pyproj 67%` mean it is still working.

*Step 3 — Configure conda to use conda-forge and avoid the default Anaconda channel* (avoids licensing issues and improves package availability):
```
conda config --add channels conda-forge
conda config --env --remove channels defaults
conda config --set channel_priority strict
```

*Step 4 — Create the environment and install movinglines:*
```
conda create -n ml python=3.9.15
conda activate ml
conda install -c samuelleblanc movinglines
```

> **Note:** If the `ml` environment already exists from a previous attempt, skip the `conda create` step and go straight to `conda activate ml`.

**If mamba itself will not install:** Skip mamba entirely and use the `libmamba` solver inside conda as shown in Step 2 above. The result is functionally equivalent — mamba is just a standalone binary that uses the same solver library.
