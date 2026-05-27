# Archon Workflows

This repository contains reusable and isolated workflows for [Archon](https://github.com/loopyd/pi-archon). 

## 🛠️ Workflow Manager (`manage.sh`)

Use the `manage.sh` utility to list, install, or uninstall workflows.

### 1. List available workflows
```bash
./manage.sh list
```

### 2. Install a workflow to a target project
* **For Local Development (creates symlinks back to this repository):**
  ```bash
  ./manage.sh install security-review /path/to/project --symlink
  ```
* **For Export/Production (copies files physically):**
  ```bash
  ./manage.sh install security-review /path/to/project
  ```

### 3. Uninstall a workflow from a project
```bash
./manage.sh uninstall security-review /path/to/project
```
