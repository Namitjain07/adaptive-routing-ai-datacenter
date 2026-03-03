#!/bin/bash
################################################################################
# Routing Comparison Results Analysis Script
# Compare ECMP vs Adaptive routing experiment results
################################################################################

set -e

RESULTS_DIR="results"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BOLD}${BLUE}"
    echo "========================================================================"
    echo "$1"
    echo "========================================================================"
    echo -e "${NC}"
}

print_section() {
    echo -e "${BOLD}${CYAN}$1${NC}"
    echo "------------------------------------------------------------------------"
}

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Compare ECMP vs Adaptive routing experiment results"
    echo ""
    echo "Options:"
    echo "  -e, --ecmp FILE       Path to ECMP results JSON file"
    echo "  -a, --adaptive FILE   Path to Adaptive results JSON file"
    echo "  -l, --latest          Use latest results (default)"
    echo "  -L, --list            List available result files"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --latest                                    # Compare latest results"
    echo "  $0 -e results/ecmp_*.json -a results/adaptive_*.json"
    echo "  $0 --list                                      # List all results"
}

list_results() {
    print_header "Available Result Files"
    
    echo -e "${BOLD}ECMP Results:${NC}"
    ls -lth "$RESULTS_DIR"/ecmp_*.json 2>/dev/null | head -10 || echo "No ECMP results found"
    
    echo ""
    echo -e "${BOLD}Adaptive Results:${NC}"
    ls -lth "$RESULTS_DIR"/adaptive_*.json 2>/dev/null | head -10 || echo "No Adaptive results found"
    
    echo ""
    echo -e "${BOLD}Comparison Results:${NC}"
    ls -lth "$RESULTS_DIR"/comparison_*.json 2>/dev/null | head -10 || echo "No comparison results found"
}

get_latest_result() {
    local pattern=$1
    ls -t "$RESULTS_DIR"/$pattern 2>/dev/null | head -1
}

compare_results() {
    local ecmp_file=$1
    local adaptive_file=$2
    
    if [ ! -f "$ecmp_file" ]; then
        echo -e "${RED}Error: ECMP file not found: $ecmp_file${NC}"
        exit 1
    fi
    
    if [ ! -f "$adaptive_file" ]; then
        echo -e "${RED}Error: Adaptive file not found: $adaptive_file${NC}"
        exit 1
    fi
    
    print_header "ROUTING COMPARISON ANALYSIS"
    
    echo -e "${BOLD}Files being compared:${NC}"
    echo "  ECMP:     $ecmp_file"
    echo "  Adaptive: $adaptive_file"
    echo ""
    
    # Extract and display experiment info
    print_section "Experiment Configuration"
    python3 << PYEOF
import json

with open('$ecmp_file') as f:
    ecmp = json.load(f)

exp = ecmp.get('experiment', {})
topo = exp.get('topology', {})

print(f"  Traffic Type:  {exp.get('traffic_type', 'N/A')}")
print(f"  Duration:      {exp.get('duration', 'N/A')} seconds")
print(f"  Topology:      {topo.get('num_spines', 0)} spines, {topo.get('num_leaves', 0)} leaves, {topo.get('hosts_per_leaf', 0)} hosts/leaf")
print(f"  Total Hosts:   {topo.get('total_hosts', 0)}")
print(f"  Timestamp:     {exp.get('timestamp', 'N/A')}")
PYEOF
    
    echo ""
    
    # Detailed comparison
    print_section "Performance Metrics Comparison"
    python3 << PYEOF
import json
import sys

ECMP_FILE = '$ecmp_file'
ADAPTIVE_FILE = '$adaptive_file'

def load_results(filename):
    with open(filename) as f:
        return json.load(f)

def calculate_fct_stats(traffic_data):
    """Calculate FCT statistics"""
    if not traffic_data:
        return None
    
    fcts = sorted([t.get('flow_completion_time', 0) for t in traffic_data if 'flow_completion_time' in t])
    
    if not fcts:
        return None
    
    n = len(fcts)
    return {
        'mean': sum(fcts) / n,
        'median': fcts[n // 2],
        'p50': fcts[int(n * 0.50)],
        'p95': fcts[int(n * 0.95)] if n > 1 else fcts[0],
        'p99': fcts[int(n * 0.99)] if n > 1 else fcts[0],
        'min': min(fcts),
        'max': max(fcts),
        'count': n
    }

def calculate_throughput_stats(traffic_data):
    """Calculate throughput statistics"""
    if not traffic_data:
        return None
    
    throughputs = [t.get('bps_received', 0) / 1e6 for t in traffic_data if 'bps_received' in t]
    
    if not throughputs:
        return None
    
    return {
        'mean': sum(throughputs) / len(throughputs),
        'total': sum(throughputs),
        'count': len(throughputs)
    }

def get_monitoring_stats(monitoring_data):
    """Extract monitoring statistics"""
    if not monitoring_data:
        return None
    
    return {
        'duration': monitoring_data.get('duration', 0),
        'packet_drops': sum(monitoring_data.get('packet_drops', {}).values()),
        'link_util': monitoring_data.get('link_utilization', {})
    }

try:
    ecmp = load_results(ECMP_FILE)
    adaptive = load_results(ADAPTIVE_FILE)
    
    ecmp_fct = calculate_fct_stats(ecmp.get('traffic', []))
    adaptive_fct = calculate_fct_stats(adaptive.get('traffic', []))
    
    ecmp_tp = calculate_throughput_stats(ecmp.get('traffic', []))
    adaptive_tp = calculate_throughput_stats(adaptive.get('traffic', []))
    
    ecmp_mon = get_monitoring_stats(ecmp.get('monitoring', {}))
    adaptive_mon = get_monitoring_stats(adaptive.get('monitoring', {}))
    
    # Print comparison table
    print(f"{'Metric':<35} {'ECMP':<18} {'Adaptive':<18} {'Improvement':<12}")
    print("=" * 83)
    
    # Flow Completion Time metrics
    if ecmp_fct and adaptive_fct:
        print("\n\033[1mFlow Completion Time (FCT):\033[0m")
        metrics = [
            ('  Total Flows', ecmp_fct['count'], adaptive_fct['count'], 'count'),
            ('  Mean FCT (s)', ecmp_fct['mean'], adaptive_fct['mean'], 'lower'),
            ('  Median FCT (s)', ecmp_fct['median'], adaptive_fct['median'], 'lower'),
            ('  P95 FCT (s)', ecmp_fct['p95'], adaptive_fct['p95'], 'lower'),
            ('  P99 Tail Latency (s)', ecmp_fct['p99'], adaptive_fct['p99'], 'lower'),
            ('  Max FCT (s)', ecmp_fct['max'], adaptive_fct['max'], 'lower'),
        ]
        
        for name, ecmp_val, adap_val, metric_type in metrics:
            if metric_type == 'count':
                print(f"{name:<35} {int(ecmp_val):<18} {int(adap_val):<18} {'-':<12}")
            else:
                change = ((adap_val - ecmp_val) / ecmp_val * 100) if ecmp_val != 0 else 0
                symbol = '✓' if (metric_type == 'lower' and change < 0) or (metric_type == 'higher' and change > 0) else '✗'
                print(f"{name:<35} {ecmp_val:<18.3f} {adap_val:<18.3f} {change:>+10.2f}% {symbol}")
    
    # Throughput metrics
    if ecmp_tp and adaptive_tp and ecmp_tp['count'] > 0:
        print("\n\033[1mThroughput:\033[0m")
        mean_change = ((adaptive_tp['mean'] - ecmp_tp['mean']) / ecmp_tp['mean'] * 100) if ecmp_tp['mean'] != 0 else 0
        symbol = '✓' if mean_change > 0 else '✗'
        print(f"{'  Mean Throughput (Mbps)':<35} {ecmp_tp['mean']:<18.2f} {adaptive_tp['mean']:<18.2f} {mean_change:>+10.2f}% {symbol}")
    
    # Monitoring metrics
    if ecmp_mon and adaptive_mon:
        print("\n\033[1mNetwork Health:\033[0m")
        print(f"{'  Packet Drops':<35} {int(ecmp_mon['packet_drops']):<18} {int(adaptive_mon['packet_drops']):<18} ", end='')
        if ecmp_mon['packet_drops'] > 0:
            reduction = ((ecmp_mon['packet_drops'] - adaptive_mon['packet_drops']) / ecmp_mon['packet_drops'] * 100)
            symbol = '✓' if reduction > 0 else '✗'
            print(f"{reduction:>+10.2f}% {symbol}")
        else:
            print(f"{'N/A':<12}")
        
        print(f"{'  Monitoring Duration (s)':<35} {ecmp_mon['duration']:<18.2f} {adaptive_mon['duration']:<18.2f} {'-':<12}")
    
    print("\n" + "=" * 83)
    
    # Summary findings
    print("\n\033[1;36mKey Findings:\033[0m")
    
    if ecmp_fct and adaptive_fct:
        p99_improvement = ((ecmp_fct['p99'] - adaptive_fct['p99']) / ecmp_fct['p99'] * 100)
        mean_improvement = ((ecmp_fct['mean'] - adaptive_fct['mean']) / ecmp_fct['mean'] * 100)
        
        if p99_improvement > 10:
            print("  \033[32m✓ Adaptive routing significantly reduces tail latency (P99)\033[0m")
        elif p99_improvement > 0:
            print("  \033[33m~ Adaptive routing slightly reduces tail latency (P99)\033[0m")
        else:
            print("  \033[31m✗ ECMP achieves better tail latency\033[0m")
        
        if mean_improvement > 10:
            print("  \033[32m✓ Adaptive routing significantly improves mean FCT\033[0m")
        elif mean_improvement > 0:
            print("  \033[33m~ Adaptive routing slightly improves mean FCT\033[0m")
        else:
            print("  \033[31m✗ ECMP achieves better mean FCT\033[0m")
    
    if ecmp_mon and adaptive_mon:
        if ecmp_mon['packet_drops'] > 0:
            reduction = ((ecmp_mon['packet_drops'] - adaptive_mon['packet_drops']) / ecmp_mon['packet_drops'] * 100)
            if reduction > 20:
                print("  \033[32m✓ Adaptive routing significantly reduces packet drops\033[0m")
            elif reduction > 0:
                print("  \033[33m~ Adaptive routing reduces packet drops\033[0m")
            else:
                print("  \033[31m✗ No improvement in packet drops\033[0m")
        else:
            print("  \033[33m~ No congestion detected in either scheme\033[0m")
    
    if ecmp_tp and adaptive_tp and ecmp_tp['count'] > 0:
        tp_improvement = ((adaptive_tp['mean'] - ecmp_tp['mean']) / ecmp_tp['mean'] * 100)
        if tp_improvement > 10:
            print("  \033[32m✓ Adaptive routing significantly improves throughput\033[0m")
        elif tp_improvement > 0:
            print("  \033[33m~ Adaptive routing slightly improves throughput\033[0m")

except Exception as e:
    print(f"Error during analysis: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
    
    echo ""
    print_header "Analysis Complete"
}

# Main script logic
ECMP_FILE=""
ADAPTIVE_FILE=""
USE_LATEST=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--ecmp)
            ECMP_FILE="$2"
            USE_LATEST=false
            shift 2
            ;;
        -a|--adaptive)
            ADAPTIVE_FILE="$2"
            USE_LATEST=false
            shift 2
            ;;
        -l|--latest)
            USE_LATEST=true
            shift
            ;;
        -L|--list)
            list_results
            exit 0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Get latest results if not specified
if [ "$USE_LATEST" = true ]; then
    ECMP_FILE=$(get_latest_result "ecmp_*.json")
    ADAPTIVE_FILE=$(get_latest_result "adaptive_*.json")
    
    if [ -z "$ECMP_FILE" ] || [ -z "$ADAPTIVE_FILE" ]; then
        echo -e "${RED}Error: Could not find latest result files${NC}"
        echo "Available results:"
        list_results
        exit 1
    fi
fi

# Run comparison
compare_results "$ECMP_FILE" "$ADAPTIVE_FILE"
