---
name: 🐛 Bug Report
about: Report a bug or unexpected behavior
title: '[BUG] '
labels: ['bug', 'needs-triage']
assignees: ''
---

## 🐛 Bug Description

<!-- A clear and concise description of what the bug is -->

## 📋 To Reproduce

Steps to reproduce the behavior:

1. Configure topology with '...'
2. Run command '...'
3. Execute experiment '...'
4. See error

## ✅ Expected Behavior

<!-- A clear and concise description of what you expected to happen -->

## ❌ Actual Behavior

<!-- What actually happened -->

## 📸 Screenshots/Logs

<!-- If applicable, add screenshots or error logs to help explain your problem -->

```
Paste error logs here
```

## 🖥️ Environment

**System Information:**
- OS: [e.g., Ubuntu 22.04, Fedora 38]
- Python Version: [e.g., 3.10.6]
- Mininet Version: [e.g., 2.3.0]
- Open vSwitch Version: [e.g., 2.17.0]

**Installation Method:**
- [ ] Installed via setup.sh
- [ ] Manual installation
- [ ] Docker (if applicable)

**Repository Version:**
- Branch: [e.g., master]
- Commit Hash: [e.g., fc50d9f]

## 📦 Dependencies

<details>
<summary>Output of `pip freeze`</summary>

```
Paste output here
```

</details>

## 🔍 Additional Context

<!-- Add any other context about the problem here -->

**Topology Configuration:**
```python
# If relevant, paste your topology configuration
```

**Experiment Parameters:**
```bash
# Command used to run the experiment
sudo python3 run_experiment.py --mode ... --routing ...
```

## ✔️ Checklist

- [ ] I have searched existing issues to ensure this is not a duplicate
- [ ] I have tested on the latest version of the code
- [ ] I have included all relevant information above
- [ ] I can reproduce this bug consistently

## 🔧 Possible Solution

<!-- Optional: If you have an idea how to fix the bug, describe it here -->
