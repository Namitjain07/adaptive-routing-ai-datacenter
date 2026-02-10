# Contributing to Adaptive Routing for AI Data Center Fabrics

Thank you for your interest in contributing to this project! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of background or identity. We expect all participants to:

- Be respectful and considerate
- Accept constructive criticism gracefully
- Focus on what's best for the project and community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing others' private information
- Any conduct that could reasonably be considered inappropriate

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/adaptive-routing-ai-datacenter.git
   cd adaptive-routing-ai-datacenter
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/Namitjain07/adaptive-routing-ai-datacenter.git
   ```
4. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

#### 🐛 Bug Fixes
- Fix routing algorithm bugs
- Correct performance measurement issues
- Resolve topology configuration problems
- Fix documentation errors

#### ✨ New Features
- New routing algorithms (e.g., CONGA, DRILL implementation)
- Additional traffic patterns (Parameter Server, Ring-AllReduce)
- Enhanced monitoring and visualization
- Support for different topologies (Fat-Tree, BCube)

#### 📚 Documentation
- Improve README, DESIGN, or other docs
- Add code comments and docstrings
- Create tutorials or examples
- Fix typos and clarify explanations

#### 🧪 Testing
- Add unit tests for routing modules
- Create integration tests for experiments
- Improve test coverage
- Add performance benchmarks

#### 🎨 Code Quality
- Refactor for better readability
- Optimize performance
- Improve error handling
- Enhance logging and debugging

## Development Setup

### Prerequisites

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y mininet openvswitch-switch python3-pip iperf3

# Python dependencies
pip install -r requirements.txt

# Development dependencies
pip install pylint flake8 black isort mypy pytest pytest-cov
```

### Running Tests

```bash
# Syntax validation
python -m py_compile routing/*.py topologies/*.py

# Installation test
python test_installation.py

# Run experiments (requires sudo for Mininet)
sudo python3 run_experiment.py --mode single --routing ecmp --duration 10
```

### Verify Your Setup

```bash
chmod +x setup.sh
./setup.sh
```

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with some modifications:

- **Line length**: Maximum 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Prefer double quotes for strings
- **Docstrings**: Use Google-style docstrings

### Code Formatting

**Use Black for automatic formatting:**
```bash
black routing/ topologies/ *.py --line-length 100
```

**Use isort for import sorting:**
```bash
isort routing/ topologies/ *.py --profile black
```

### Linting

**Run flake8:**
```bash
flake8 routing/ topologies/ *.py --max-line-length 100
```

**Run pylint:**
```bash
pylint routing/ topologies/ *.py --max-line-length 100
```

### Example Code Style

```python
"""
Module for implementing adaptive routing algorithms.

This module provides flowlet-based and congestion-aware routing
for data center networks.
"""

import time
import threading
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


class AdaptiveRouter:
    """
    Implements adaptive routing with flowlet switching.
    
    Attributes:
        flowlet_timeout: Time threshold for flowlet detection (seconds)
        path_loads: Dictionary mapping path IDs to load estimates
    """
    
    def __init__(self, flowlet_timeout: float = 0.05):
        """
        Initialize the adaptive router.
        
        Args:
            flowlet_timeout: Maximum idle time to consider same flowlet (default: 50ms)
        """
        self.flowlet_timeout = flowlet_timeout
        self.path_loads: Dict[int, float] = defaultdict(float)
        
    def select_path(
        self, 
        flow_id: str, 
        available_paths: List[int],
        current_time: float
    ) -> int:
        """
        Select optimal path for the given flow.
        
        Args:
            flow_id: Unique flow identifier
            available_paths: List of available path IDs
            current_time: Current timestamp
            
        Returns:
            Selected path ID
            
        Raises:
            ValueError: If no paths are available
        """
        if not available_paths:
            raise ValueError("No available paths for routing")
            
        # Implementation here
        return min(available_paths, key=lambda p: self.path_loads[p])
```

## Testing Guidelines

### Writing Tests

1. **Test file naming**: `test_<module_name>.py`
2. **Test function naming**: `test_<functionality>_<scenario>()`
3. **Use descriptive assertions**: Include helpful error messages

### Example Test

```python
def test_flowlet_router_path_selection():
    """Test that flowlet router selects least-loaded path."""
    router = FlowletRouter(flowlet_timeout=0.05)
    router.path_loads[0] = 0.8  # High load
    router.path_loads[1] = 0.3  # Low load
    
    path = router.select_path("flow1", [0, 1], time.time())
    
    assert path == 1, "Router should select least-loaded path"
```

### Coverage Requirements

- Aim for **>80% code coverage** for new features
- All critical paths must be tested
- Include edge cases and error conditions

## Commit Guidelines

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Examples

```bash
# Feature
git commit -m "feat(routing): Add CONGA adaptive routing implementation"

# Bug fix
git commit -m "fix(topology): Correct link bandwidth configuration in leaf-spine"

# Documentation
git commit -m "docs(README): Add installation instructions for Fedora"

# Multi-line with body
git commit -m "feat(traffic): Add Parameter Server traffic pattern

Implements many-to-one traffic generation for parameter server
architecture simulation. Includes configurable server count and
gradient aggregation timing.

Closes #42"
```

### Commit Best Practices

- **One logical change per commit**
- **Write clear, descriptive messages**
- **Reference issues**: Use "Fixes #123" or "Closes #456"
- **Keep commits atomic**: Each commit should be independently functional

## Pull Request Process

### Before Submitting

1. **Update your branch** with latest upstream:
   ```bash
   git fetch upstream
   git rebase upstream/master
   ```

2. **Run all checks**:
   ```bash
   black --check routing/ topologies/ *.py
   flake8 routing/ topologies/ *.py
   python test_installation.py
   ```

3. **Test your changes**:
   ```bash
   sudo python3 run_experiment.py --mode single --routing ecmp --duration 10
   ```

4. **Update documentation** if needed

### Submitting PR

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create Pull Request** on GitHub with:
   - Clear title following commit convention
   - Detailed description of changes
   - Reference to related issues
   - Screenshots/results if applicable

3. **PR Template**:
   ```markdown
   ## Description
   Brief description of what this PR does.
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation update
   - [ ] Performance improvement
   
   ## Testing Done
   - [ ] Unit tests added/updated
   - [ ] Manual testing completed
   - [ ] All existing tests pass
   
   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Documentation updated
   - [ ] No new warnings introduced
   - [ ] Backward compatible (or breaking changes documented)
   
   ## Related Issues
   Fixes #(issue number)
   ```

### Review Process

1. **CI checks must pass** (all GitHub Actions workflows)
2. **At least one approval** from maintainers
3. **Address review feedback** promptly
4. **Rebase if needed** to resolve conflicts

### After Approval

- Maintainers will merge using **squash and merge** strategy
- Your contribution will be credited in release notes

## Reporting Bugs

### Before Reporting

1. **Check existing issues** to avoid duplicates
2. **Verify** it's actually a bug (not expected behavior)
3. **Test** on latest version

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the bug.

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. Configure topology with '...'
3. Observe error '...'

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.10.6]
- Mininet version: [e.g., 2.3.0]

**Logs/Screenshots**
```
Error output or screenshots
```

**Additional context**
Any other relevant information.
```

## Suggesting Enhancements

### Enhancement Proposal Template

```markdown
**Feature Description**
Clear description of the proposed feature.

**Motivation**
Why is this feature needed? What problem does it solve?

**Proposed Implementation**
High-level overview of how it could be implemented.

**Alternatives Considered**
Other approaches you've thought about.

**Additional Context**
Any other relevant information, references, or examples.
```

## Questions?

- **Open an issue** with the `question` label
- **Discussion forum**: Use GitHub Discussions
- **Email**: Contact project maintainers

## Recognition

Contributors will be:
- Listed in release notes
- Credited in documentation
- Added to CONTRIBUTORS.md (if significant contributions)

Thank you for contributing to advancing AI data center networking research! 🚀
