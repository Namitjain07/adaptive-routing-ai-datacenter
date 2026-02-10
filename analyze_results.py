#!/usr/bin/env python3
"""
Analysis and Visualization Tools
Analyze experimental results and generate plots.
"""

import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict


class ResultsAnalyzer:
    """Analyze routing experiment results"""
    
    def __init__(self, results_file):
        """
        Args:
            results_file: Path to JSON results file
        """
        with open(results_file, 'r') as f:
            self.data = json.load(f)
    
    def analyze_throughput(self):
        """Analyze throughput statistics"""
        if 'traffic' not in self.data or not self.data['traffic']:
            return None
        
        throughputs = []
        fcts = []  # Flow Completion Times
        for flow in self.data['traffic']:
            if 'bps_received' in flow:
                throughputs.append(flow['bps_received'] / 1e6)  # Convert to Mbps
            if 'flow_completion_time' in flow:
                fcts.append(flow['flow_completion_time'])
        
        if not throughputs:
            return None
        
        result = {
            'mean_mbps': np.mean(throughputs),
            'median_mbps': np.median(throughputs),
            'std_mbps': np.std(throughputs),
            'min_mbps': np.min(throughputs),
            'max_mbps': np.max(throughputs),
            'total_flows': len(throughputs)
        }
        
        # Add tail latency metrics (FCT)
        if fcts:
            result['fct_mean'] = np.mean(fcts)
            result['fct_median'] = np.median(fcts)
            result['fct_p95'] = np.percentile(fcts, 95)
            result['fct_p99'] = np.percentile(fcts, 99)
            result['fct_max'] = np.max(fcts)
        
        return result
    
    def analyze_utilization(self):
        """Analyze link utilization statistics"""
        if 'monitoring' not in self.data:
            return None
        
        link_util = self.data['monitoring'].get('link_utilization', {})
        
        if not link_util:
            return None
        
        mean_utils = [stats['mean'] for stats in link_util.values()]
        max_utils = [stats['max'] for stats in link_util.values()]
        
        return {
            'avg_mean_util': np.mean(mean_utils),
            'avg_max_util': np.mean(max_utils),
            'std_util': np.std(mean_utils),
            'balance_score': 1.0 - (np.std(mean_utils) / np.mean(mean_utils)) if np.mean(mean_utils) > 0 else 0,
            'num_links': len(link_util)
        }
    
    def analyze_drops(self):
        """Analyze packet drop statistics"""
        if 'monitoring' not in self.data:
            return None
        
        drops = self.data['monitoring'].get('packet_drops', {})
        
        total_drops = sum(drops.values()) if drops else 0
        
        return {
            'total_drops': total_drops,
            'num_congested_links': len(drops),
            'avg_drops_per_link': total_drops / len(drops) if drops else 0
        }
    
    def get_summary(self):
        """Get comprehensive analysis summary"""
        summary = {
            'experiment': self.data.get('experiment', {}),
            'throughput': self.analyze_throughput(),
            'utilization': self.analyze_utilization(),
            'drops': self.analyze_drops()
        }
        
        return summary
    
    def print_summary(self):
        """Print analysis summary"""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("EXPERIMENT ANALYSIS")
        print("="*60)
        
        exp = summary['experiment']
        print(f"\nRouting Scheme: {exp.get('routing_scheme', 'N/A')}")
        print(f"Traffic Type: {exp.get('traffic_type', 'N/A')}")
        print(f"Duration: {exp.get('duration', 'N/A')} seconds")
        
        if summary['throughput']:
            print("\n### Throughput ###")
            tp = summary['throughput']
            print(f"  Mean: {tp['mean_mbps']:.2f} Mbps")
            print(f"  Median: {tp['median_mbps']:.2f} Mbps")
            print(f"  Std Dev: {tp['std_mbps']:.2f} Mbps")
            print(f"  Range: [{tp['min_mbps']:.2f}, {tp['max_mbps']:.2f}] Mbps")
            print(f"  Total Flows: {tp['total_flows']}")
            
            # Print tail latency if available
            if 'fct_mean' in tp:
                print("\n### Flow Completion Time (Tail Latency) ###")
                print(f"  Mean FCT: {tp['fct_mean']:.3f} seconds")
                print(f"  Median FCT: {tp['fct_median']:.3f} seconds")
                print(f"  P95 FCT: {tp['fct_p95']:.3f} seconds")
                print(f"  P99 FCT: {tp['fct_p99']:.3f} seconds")
                print(f"  Max FCT: {tp['fct_max']:.3f} seconds")
        
        if summary['utilization']:
            print("\n### Link Utilization ###")
            util = summary['utilization']
            print(f"  Average: {util['avg_mean_util']:.2f}%")
            print(f"  Std Dev: {util['std_util']:.2f}%")
            print(f"  Balance Score: {util['balance_score']:.3f}")
            print(f"  Number of Links: {util['num_links']}")
        
        if summary['drops']:
            print("\n### Packet Drops ###")
            drops = summary['drops']
            print(f"  Total Drops: {drops['total_drops']}")
            print(f"  Congested Links: {drops['num_congested_links']}")
            print(f"  Avg Drops/Link: {drops['avg_drops_per_link']:.2f}")
        
        print("="*60)


class ComparisonAnalyzer:
    """Compare ECMP vs Adaptive routing results"""
    
    def __init__(self, ecmp_file, adaptive_file):
        """
        Args:
            ecmp_file: Path to ECMP results
            adaptive_file: Path to Adaptive results
        """
        self.ecmp_analyzer = ResultsAnalyzer(ecmp_file)
        self.adaptive_analyzer = ResultsAnalyzer(adaptive_file)
    
    def compare_metrics(self):
        """Compare key metrics"""
        ecmp_summary = self.ecmp_analyzer.get_summary()
        adaptive_summary = self.adaptive_analyzer.get_summary()
        
        comparison = {}
        
        # Compare throughput
        if ecmp_summary['throughput'] and adaptive_summary['throughput']:
            ecmp_tp = ecmp_summary['throughput']['mean_mbps']
            adaptive_tp = adaptive_summary['throughput']['mean_mbps']
            improvement = ((adaptive_tp - ecmp_tp) / ecmp_tp) * 100 if ecmp_tp > 0 else 0
            
            comparison['throughput'] = {
                'ecmp': ecmp_tp,
                'adaptive': adaptive_tp,
                'improvement_pct': improvement
            }
        
        # Compare utilization balance
        if ecmp_summary['utilization'] and adaptive_summary['utilization']:
            ecmp_balance = ecmp_summary['utilization']['balance_score']
            adaptive_balance = adaptive_summary['utilization']['balance_score']
            improvement = ((adaptive_balance - ecmp_balance) / ecmp_balance) * 100 if ecmp_balance > 0 else 0
            
            comparison['balance'] = {
                'ecmp': ecmp_balance,
                'adaptive': adaptive_balance,
                'improvement_pct': improvement
            }
        
        # Compare packet drops
        if ecmp_summary['drops'] and adaptive_summary['drops']:
            ecmp_drops = ecmp_summary['drops']['total_drops']
            adaptive_drops = adaptive_summary['drops']['total_drops']
            reduction = ((ecmp_drops - adaptive_drops) / ecmp_drops) * 100 if ecmp_drops > 0 else 0
            
            comparison['drops'] = {
                'ecmp': ecmp_drops,
                'adaptive': adaptive_drops,
                'reduction_pct': reduction
            }
        
        # Compare tail latency (FCT)
        if (ecmp_summary['throughput'] and adaptive_summary['throughput'] and 
            'fct_p99' in ecmp_summary['throughput'] and 'fct_p99' in adaptive_summary['throughput']):
            ecmp_fct = ecmp_summary['throughput']['fct_p99']
            adaptive_fct = adaptive_summary['throughput']['fct_p99']
            improvement = ((ecmp_fct - adaptive_fct) / ecmp_fct) * 100 if ecmp_fct > 0 else 0
            
            comparison['tail_latency'] = {
                'ecmp_p99': ecmp_fct,
                'adaptive_p99': adaptive_fct,
                'improvement_pct': improvement
            }
        
        return comparison
    
    def print_comparison(self):
        """Print comparison results"""
        comparison = self.compare_metrics()
        
        print("\n" + "="*70)
        print("ECMP vs ADAPTIVE ROUTING COMPARISON")
        print("="*70)
        
        print(f"\n{'Metric':<30} {'ECMP':<15} {'Adaptive':<15} {'Change':<10}")
        print("-" * 70)
        
        if 'throughput' in comparison:
            tp = comparison['throughput']
            print(f"{'Throughput (Mbps)':<30} {tp['ecmp']:<15.2f} {tp['adaptive']:<15.2f} {tp['improvement_pct']:>+9.2f}%")
        
        if 'balance' in comparison:
            bal = comparison['balance']
            print(f"{'Load Balance Score':<30} {bal['ecmp']:<15.3f} {bal['adaptive']:<15.3f} {bal['improvement_pct']:>+9.2f}%")
        
        if 'drops' in comparison:
            drops = comparison['drops']
            print(f"{'Packet Drops':<30} {drops['ecmp']:<15} {drops['adaptive']:<15} {drops['reduction_pct']:>+9.2f}%")
        
        if 'tail_latency' in comparison:
            tl = comparison['tail_latency']
            print(f"{'Tail Latency P99 (s)':<30} {tl['ecmp_p99']:<15.3f} {tl['adaptive_p99']:<15.3f} {tl['improvement_pct']:>+9.2f}%")
        
        print("="*70)
        
        # Print interpretation
        print("\n### Key Findings ###")
        if 'throughput' in comparison:
            if comparison['throughput']['improvement_pct'] > 5:
                print("✓ Adaptive routing shows significant throughput improvement")
            elif comparison['throughput']['improvement_pct'] > 0:
                print("~ Adaptive routing shows marginal throughput improvement")
            else:
                print("✗ ECMP achieves better throughput")
        
        if 'balance' in comparison:
            if comparison['balance']['improvement_pct'] > 10:
                print("✓ Adaptive routing significantly improves load balance")
            elif comparison['balance']['improvement_pct'] > 0:
                print("~ Adaptive routing slightly improves load balance")
            else:
                print("✗ ECMP achieves better load balance")
        
        if 'drops' in comparison:
            if comparison['drops']['reduction_pct'] > 20:
                print("✓ Adaptive routing significantly reduces packet drops")
            elif comparison['drops']['reduction_pct'] > 0:
                print("~ Adaptive routing reduces packet drops")
            else:
                print("✗ No improvement in packet drops")
        
        if 'tail_latency' in comparison:
            if comparison['tail_latency']['improvement_pct'] > 10:
                print("✓ Adaptive routing significantly reduces tail latency (P99)")
            elif comparison['tail_latency']['improvement_pct'] > 0:
                print("~ Adaptive routing reduces tail latency (P99)")
            else:
                print("✗ ECMP achieves better tail latency")
        
        print()
    
    def plot_comparison(self, output_file='comparison_plot.png'):
        """Generate comparison plots"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle('ECMP vs Adaptive Routing Comparison', fontsize=16, fontweight='bold')
        
        ecmp_summary = self.ecmp_analyzer.get_summary()
        adaptive_summary = self.adaptive_analyzer.get_summary()
        
        # Plot 1: Throughput comparison
        ax = axes[0, 0]
        if ecmp_summary['throughput'] and adaptive_summary['throughput']:
            schemes = ['ECMP', 'Adaptive']
            throughputs = [
                ecmp_summary['throughput']['mean_mbps'],
                adaptive_summary['throughput']['mean_mbps']
            ]
            ax.bar(schemes, throughputs, color=['#3498db', '#2ecc71'])
            ax.set_ylabel('Throughput (Mbps)')
            ax.set_title('Average Throughput')
            ax.grid(True, alpha=0.3)
        
        # Plot 2: Load balance
        ax = axes[0, 1]
        if ecmp_summary['utilization'] and adaptive_summary['utilization']:
            schemes = ['ECMP', 'Adaptive']
            balance_scores = [
                ecmp_summary['utilization']['balance_score'],
                adaptive_summary['utilization']['balance_score']
            ]
            ax.bar(schemes, balance_scores, color=['#3498db', '#2ecc71'])
            ax.set_ylabel('Balance Score')
            ax.set_title('Load Balance (Higher is Better)')
            ax.set_ylim([0, 1])
            ax.grid(True, alpha=0.3)
        
        # Plot 3: Packet drops
        ax = axes[1, 0]
        if ecmp_summary['drops'] and adaptive_summary['drops']:
            schemes = ['ECMP', 'Adaptive']
            drops = [
                ecmp_summary['drops']['total_drops'],
                adaptive_summary['drops']['total_drops']
            ]
            ax.bar(schemes, drops, color=['#e74c3c', '#f39c12'])
            ax.set_ylabel('Packet Drops')
            ax.set_title('Total Packet Drops (Lower is Better)')
            ax.grid(True, alpha=0.3)
        
        # Plot 4: Utilization distribution
        ax = axes[1, 1]
        if ecmp_summary['utilization'] and adaptive_summary['utilization']:
            ax.text(0.5, 0.5, 'Utilization\nDistribution\n(Reserved for detailed plot)',
                   ha='center', va='center', fontsize=12)
            ax.set_title('Link Utilization Distribution')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"*** Comparison plot saved to {output_file}")
        plt.close()


def main():
    parser = argparse.ArgumentParser(description='Analyze routing experiment results')
    
    parser.add_argument('--mode',
                       choices=['single', 'compare'],
                       default='single',
                       help='Analysis mode')
    
    parser.add_argument('--file',
                       help='Single results file to analyze')
    
    parser.add_argument('--ecmp',
                       help='ECMP results file (for comparison mode)')
    
    parser.add_argument('--adaptive',
                       help='Adaptive results file (for comparison mode)')
    
    parser.add_argument('--plot',
                       action='store_true',
                       help='Generate plots')
    
    parser.add_argument('--output',
                       default='comparison_plot.png',
                       help='Output plot filename')
    
    args = parser.parse_args()
    
    if args.mode == 'single':
        if not args.file:
            print("Error: --file required for single mode")
            return
        
        analyzer = ResultsAnalyzer(args.file)
        analyzer.print_summary()
    
    else:  # compare mode
        if not args.ecmp or not args.adaptive:
            print("Error: --ecmp and --adaptive required for compare mode")
            return
        
        comparator = ComparisonAnalyzer(args.ecmp, args.adaptive)
        comparator.print_comparison()
        
        if args.plot:
            comparator.plot_comparison(args.output)


if __name__ == '__main__':
    main()
