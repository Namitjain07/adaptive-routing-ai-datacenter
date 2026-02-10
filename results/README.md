# Results Directory

This directory contains experimental results in JSON format.

## File Naming Convention

- `ecmp_<traffic-type>_<timestamp>.json` - ECMP routing results
- `adaptive_<traffic-type>_<timestamp>.json` - Adaptive routing results
- `comparison_<traffic-type>_<timestamp>.json` - Comparison results

## Result Structure

Each result file contains:
- Experiment configuration (topology, routing, traffic parameters)
- Traffic flow statistics (throughput, bytes transferred)
- Network monitoring data (link utilization, packet drops)
- Derived metrics (FCT, load balance, etc.)

Results are automatically saved here by `run_experiment.py`.
