# ruitu_tasks

Task collection for Ruitu multimodal EEG and eye-tracking experiments.

## Tasks

- `task_rest/`: resting-state PsychoPy task with LSL markers, Gazepoint GP3 LSL tooling, LabRecorder checks, and XDF verification.

## Windows Setup

Clone the repository, then enter the task folder before creating the Python environment:

```powershell
git clone https://github.com/chienming-lo/ruitu_tasks.git
cd ruitu_tasks\task_rest
uv venv --python 3.10
uv sync --extra dev
```

See `task_rest/docs/windows_software_setup.md` and `task_rest/docs/windows_runbook.md` for the experiment runbook.
