#!/usr/bin/env python3
"""
Collision Test Results Analyzer
Visualize and compare ECMP vs Adaptive routing collision test results.
"""

import json
import argparse
import sys
from pathlib import Path
import numpy as np

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available, skipping plots")


class CollisionResultsAnalyzer:
    """Analyze collision test results"""
    
    def __init__(self, result_file):
        with open(result_file, 'r') as f:
            self.data = json.load(f)
    
    def print_summary(self):
        """Print comprehensive summary"""
        print("\n" + "="*80)
        print("COLLISION TEST RESULTS SUMMARY")
        print("="*80)
        
        for test_name, results in self.data.items():
            print(f"\n### {test_name.upper().replace('_', ' ')} ###")
            
            ecmp = results.get('ecmp', {})
            adaptive = results.get('adaptive', {})
            
            self._compare_metrics(ecmp, adaptive)
    
    def _compare_metrics(self, ecmp, adaptive):
        """Compare metrics between ECMP and Adaptive"""
        
        # Balance score
        ecmp_balance = ecmp.get('balance_score', 0)
        adaptive_balance = adaptive.get('balance_score', 0)
        
        print(f"\n  Balance Score (higher is better):")
        print(f"    ECMP:     {ecmp_balance:.3f}")
        print(f"    Adaptive: {adaptive_balance:.3f}")
        
        if adaptive_balance > ecmp_balance and ecmp_balance > 0:
            improvement = ((adaptive_balance - ecmp_balance) / ecmp_balance * 100)
            print(f"    ✓ Improvement: +{improvement:.1f}%")
        elif adaptive_balance > ecmp_balance:
            print(f"    ✓ Adaptive is better")
        else:
            print(f"    ✗ No improvement")
        
        # Imbalance factor
        ecmp_imbalance = ecmp.get('imbalance_factor', 1.0)
        adaptive_imbalance = adaptive.get('imbalance_factor', 1.0)
        
        print(f"\n  Imbalance Factor (lower is better):")
        print(f"    ECMP:     {ecmp_imbalance:.2f}x")
        print(f"    Adaptive: {adaptive_imbalance:.2f}x")
        
        if adaptive_imbalance < ecmp_imbalance and ecmp_imbalance > 1.0:
            reduction = ((ecmp_imbalance - adaptive_imbalance) / (ecmp_imbalance - 1.0) * 100)
            print(f"    ✓ Reduction: -{reduction:.1f}%")
        elif adaptive_imbalance < ecmp_imbalance:
            print(f"    ✓ Adaptive is better")
        else:
            print(f"    ✗ No improvement")
        
        # Packet drops
        ecmp_drops = ecmp.get('total_drops', 0)
        adaptive_drops = adaptive.get('total_drops', 0)
        
        print(f"\n  Packet Drops (lower is better):")
        print(f"    ECMP:     {ecmp_drops}")
        print(f"    Adaptive: {adaptive_drops}")
        
        if adaptive_drops < ecmp_drops:
            reduction = ecmp_drops - adaptive_drops
            pct = (reduction / ecmp_drops * 100) if ecmp_drops > 0 else 0
            print(f"    ✓ Reduction: -{reduction} drops (-{pct:.1f}%)")
        elif ecmp_drops == 0 and adaptive_drops == 0:
            print(f"    → No drops in either scheme")
        else:
            print(f"    ✗ No improvement")
        
        # Overall assessment
        print(f"\n  Overall Assessment:")
        improvements = 0
        if adaptive_balance > ecmp_balance:
            improvements += 1
        if adaptive_imbalance < ecmp_imbalance:
            improvements += 1
        if adaptive_drops < ecmp_drops or (ecmp_drops == 0 and adaptive_drops == 0):
            improvements += 1
        
        if improvements >= 2:
            print(f"    ✓✓ ADAPTIVE ROUTING WINS ({improvements}/3 metrics improved)")
        elif improvements == 1:
            print(f"    → Mixed results ({improvements}/3 metrics improved)")
        else:
            print(f"    ✗ ECMP performs similarly or better")
    
    def generate_plots(self, output_dir='collision_plots'):
        """Generate comparison plots"""
        if not HAS_MATPLOTLIB:
            print("Matplotlib not available, skipping plots")
            return
        
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n*** Generating plots in {output_dir}/...")
        
        # Plot 1: Balance Score Comparison
        self._plot_balance_scores(output_dir)
        
        # Plot 2: Imbalance Factor Comparison
        self._plot_imbalance_factors(output_dir)
        
        # Plot 3: Packet Drops Comparison
        self._plot_packet_drops(output_dir)
        
        print(f"*** Plots saved to {output_dir}/")
    
    def _plot_balance_scores(self, output_dir):
        """Plot balance score comparison"""
        test_names = []
        ecmp_scores = []
        adaptive_scores = []
        
        for test_name, results in self.data.items():
            test_names.append(test_name.replace('_', '\n'))
            ecmp_scores.append(results.get('ecmp', {}).get('balance_score', 0))
            adaptive_scores.append(results.get('adaptive', {}).get('balance_score', 0))
        
        x = np.arange(len(test_names))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars1 = ax.bar(x - width/2, ecmp_scores, width, label='ECMP', color='#ff6b6b')
        bars2 = ax.bar(x + width/2, adaptive_scores, width, label='Adaptive', color='#4ecdc4')
        
        ax.set_ylabel('Balance Score (higher is better)', fontsize=12)
        ax.set_title('Load Balance Comparison: ECMP vs Adaptive Routing', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(test_names)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=0.85, color='green', linestyle='--', alpha=0.5, label='Target (0.85)')
        
        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.2f}',
                       ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/balance_score_comparison.png', dpi=300)
        plt.close()
        print(f"  ✓ {output_dir}/balance_score_comparison.png")
    
    def _plot_imbalance_factors(self, output_dir):
        """Plot imbalance factor comparison"""
        test_names = []
        ecmp_factors = []
        adaptive_factors = []
        
        for test_name, results in self.data.items():
            test_names.append(test_name.replace('_', '\n'))
            ecmp_factors.append(results.get('ecmp', {}).get('imbalance_factor', 1.0))
            adaptive_factors.append(results.get('adaptive', {}).get('imbalance_factor', 1.0))
        
        x = np.arange(len(test_names))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars1 = ax.bar(x - width/2, ecmp_factors, width, label='ECMP', color='#ff6b6b')
        bars2 = ax.bar(x + width/2, adaptive_factors, width, label='Adaptive', color='#4ecdc4')
        
        ax.set_ylabel('Imbalance Factor (lower is better)', fontsize=12)
        ax.set_title('Path Imbalance: ECMP vs Adaptive Routing', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(test_names)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=1.0, color='green', linestyle='--', alpha=0.5, label='Perfect (1.0)')
        ax.axhline(y=1.3, color='orange', linestyle='--', alpha=0.5, label='Target (<1.3)')
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.2f}x',
                       ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/imbalance_factor_comparison.png', dpi=300)
        plt.close()
        print(f"  ✓ {output_dir}/imbalance_factor_comparison.png")
    
    def _plot_packet_drops(self, output_dir):
        """Plot packet drops comparison"""
        test_names = []
        ecmp_drops = []
        adaptive_drops = []
        
        for test_name, results in self.data.items():
            test_names.append(test_name.replace('_', '\n'))
            ecmp_drops.append(results.get('ecmp', {}).get('total_drops', 0))
            adaptive_drops.append(results.get('adaptive', {}).get('total_drops', 0))
        
        x = np.arange(len(test_names))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(10, 6))
        bars1 = ax.bar(x - width/2, ecmp_drops, width, label='ECMP', color='#ff6b6b')
        bars2 = ax.bar(x + width/2, adaptive_drops, width, label='Adaptive', color='#4ecdc4')
        
        ax.set_ylabel('Packet Drops (lower is better)', fontsize=12)
        ax.set_title('Congestion Impact: ECMP vs Adaptive Routing', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(test_names)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/packet_drops_comparison.png', dpi=300)
        plt.close()
        print(f"  ✓ {output_dir}/packet_drops_comparison.png")
    
    def export_summary_table(self, output_file='collision_summary.md'):
        """Export results as markdown table"""
        with open(output_file, 'w') as f:
            f.write("# Collision Test Results Summary\n\n")
            
            for test_name, results in self.data.items():
                f.write(f"## {test_name.replace('_', ' ').title()}\n\n")
                
                ecmp = results.get('ecmp', {})
                adaptive = results.get('adaptive', {})
                
                f.write("| Metric | ECMP | Adaptive | Improvement |\n")
                f.write("|--------|------|----------|-------------|\n")
                
                # Balance score
                ecmp_bal = ecmp.get('balance_score', 0)
                adap_bal = adaptive.get('balance_score', 0)
                imp = ((adap_bal - ecmp_bal) / ecmp_bal * 100) if ecmp_bal > 0 else 0
                f.write(f"| Balance Score | {ecmp_bal:.3f} | {adap_bal:.3f} | +{imp:.1f}% |\n")
                
                # Imbalance factor
                ecmp_imb = ecmp.get('imbalance_factor', 1.0)
                adap_imb = adaptive.get('imbalance_factor', 1.0)
                imp = ((ecmp_imb - adap_imb) / ecmp_imb * 100) if ecmp_imb > 1.0 else 0
                f.write(f"| Imbalance Factor | {ecmp_imb:.2f}x | {adap_imb:.2f}x | -{imp:.1f}% |\n")
                
                # Drops
                ecmp_drops = ecmp.get('total_drops', 0)
                adap_drops = adaptive.get('total_drops', 0)
                f.write(f"| Packet Drops | {ecmp_drops} | {adap_drops} | {ecmp_drops - adap_drops} fewer |\n")
                
                f.write("\n")
        
        print(f"\n*** Summary table exported to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze collision test results'
    )
    parser.add_argument('result_file',
                       help='JSON result file from collision tests')
    parser.add_argument('--plot',
                       action='store_true',
                       help='Generate plots')
    parser.add_argument('--export',
                       action='store_true',
                       help='Export markdown summary')
    parser.add_argument('--output',
                       default='collision_plots',
                       help='Output directory for plots')
    
    args = parser.parse_args()
    
    if not Path(args.result_file).exists():
        print(f"Error: File not found: {args.result_file}")
        sys.exit(1)
    
    # Analyze results
    analyzer = CollisionResultsAnalyzer(args.result_file)
    analyzer.print_summary()
    
    if args.plot:
        analyzer.generate_plots(output_dir=args.output)
    
    if args.export:
        analyzer.export_summary_table()


if __name__ == '__main__':
    main()
