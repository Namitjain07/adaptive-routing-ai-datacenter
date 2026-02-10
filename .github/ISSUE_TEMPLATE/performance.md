---
name: 🚀 Performance Issue
about: Report performance problems or optimization opportunities
title: '[PERF] '
labels: ['performance', 'needs-triage']
assignees: ''
---

## 🚀 Performance Issue

**Component Affected:**

- [ ] Routing algorithm (ECMP/Adaptive)
- [ ] Traffic generation
- [ ] Topology setup
- [ ] Monitoring/data collection
- [ ] Results analysis
- [ ] Other: [specify]

## 📊 Current Performance

<!-- Describe the current performance characteristics -->

**Metrics:**
- Execution Time: [e.g., 5 minutes for 30-second experiment]
- Memory Usage: [e.g., 2GB]
- CPU Usage: [e.g., 80% on all cores]
- Network Throughput: [e.g., only 40% of theoretical maximum]

## 🎯 Expected Performance

<!-- What performance do you expect or need? -->

**Target Metrics:**
- Execution Time: [e.g., should be < 2 minutes]
- Memory Usage: [e.g., should use < 1GB]
- Network Throughput: [e.g., should achieve > 80%]

## 📋 To Reproduce

**Configuration:**
```bash
# Commands or configuration that reproduce the performance issue
sudo python3 run_experiment.py ...
```

**Topology:**
- Spines: [e.g., 4]
- Leaves: [e.g., 4]
- Hosts: [e.g., 16 total]

**Traffic Pattern:**
- Type: [e.g., all-to-all]
- Duration: [e.g., 30 seconds]
- Flow count: [e.g., 240 flows]

## 🖥️ Environment

- OS: [e.g., Ubuntu 22.04]
- CPU: [e.g., Intel i7-10700K, 8 cores]
- RAM: [e.g., 16GB]
- Python Version: [e.g., 3.10.6]

## 📈 Profiling Data

<!-- If you've done any profiling, include the results -->

<details>
<summary>Profiling Output</summary>

```
Paste profiling data here (e.g., from cProfile)
```

</details>

## 💡 Potential Causes

<!-- If you have ideas about what might be causing the performance issue -->

## 🔧 Suggested Optimizations

<!-- If you have ideas for how to improve performance -->

## ✔️ Checklist

- [ ] I have searched existing issues for similar performance problems
- [ ] I have provided detailed performance metrics
- [ ] I can consistently reproduce this performance issue
- [ ] I have included environment details

## 📊 Benchmark Results

<!-- If you've compared with expected or baseline performance -->

| Metric | Current | Expected | Difference |
|--------|---------|----------|------------|
| Throughput | | | |
| Latency | | | |
| CPU Usage | | | |
| Memory | | | |
