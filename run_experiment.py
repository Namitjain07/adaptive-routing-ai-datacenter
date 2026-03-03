#!/usr/bin/env python3
"""
Main Experiment Runner
Compare ECMP vs Adaptive Routing for AI Data Center Traffic
"""

import sys
import argparse
import time
import json
import signal
import logging
from datetime import datetime

sys.path.append('/home/namitjain07/Desktop/NAI')

from utils.logger import setup_logger, get_logger

# Global cleanup function
cleanup_net = None

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    logger = get_logger()
    logger.warning("\nInterrupt received - cleaning up...")
    if cleanup_net:
        cleanup_net.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

from topologies.leaf_spine import create_network
from routing.ecmp_routing import setup_ecmp_routing
from routing.adaptive_routing import setup_adaptive_routing
from routing.traffic_generator import AITrafficGenerator, run_traffic_test
from routing.monitor import NetworkMonitor, FlowCompletionTracker


class ExperimentRunner:
    """
    Run routing comparison experiments.
    """
    
    def __init__(self, num_spines=4, num_leaves=4, hosts_per_leaf=4):
        self.num_spines = num_spines
        self.num_leaves = num_leaves
        self.hosts_per_leaf = hosts_per_leaf
        self.results = {}
        self.logger = get_logger()
    
    def run_experiment(self, routing_scheme='ecmp', traffic_type='all_to_all',
                      duration=10, output_dir='results'):
        """
        Run a single experiment.
        
        Args:
            routing_scheme: 'ecmp' or 'adaptive'
            traffic_type: 'all_to_all', 'allreduce', or 'bursty'
            duration: Experiment duration in seconds
            output_dir: Directory to save results
        """
        global cleanup_net
        
        self.logger.info("="*70)
        self.logger.info(f"EXPERIMENT: {routing_scheme.upper()} Routing with {traffic_type} Traffic")
        self.logger.info("="*70)
        
        # Create network
        self.logger.info("Creating network...")
        net = create_network(
            num_spines=self.num_spines,
            num_leaves=self.num_leaves,
            hosts_per_leaf=self.hosts_per_leaf
        )
        cleanup_net = net  # Set for signal handler
        
        # Start network
        self.logger.info("Starting network...")
        net.start()
        time.sleep(2)
        
        # Install routing
        self.logger.info(f"Installing {routing_scheme} routing...")
        if routing_scheme == 'ecmp':
            router, routing_table = setup_ecmp_routing(
                net, 
                num_spines=self.num_spines,
                num_leaves=self.num_leaves,
                hosts_per_leaf=self.hosts_per_leaf
            )
        else:  # adaptive
            router = setup_adaptive_routing(
                net,
                num_spines=self.num_spines,
                num_leaves=self.num_leaves,
                hosts_per_leaf=self.hosts_per_leaf,
                mode='flowlet'
            )
        
        time.sleep(2)
        
        # Test connectivity (limited test to avoid hanging)
        self.logger.info("Testing basic connectivity...")
        hosts = net.hosts
        if len(hosts) >= 2:
            result = hosts[0].cmd(f'ping -c 1 -W 2 {hosts[1].IP()}')
            if 'bytes from' in result:
                self.logger.info(f"Connectivity verified: {hosts[0].name} -> {hosts[1].name}")
            else:
                self.logger.warning("Limited connectivity detected")
        
        # Start monitoring
        self.logger.info("Starting network monitoring...")
        monitor = NetworkMonitor(net, sample_interval=1.0)
        monitor.start()
        
        # Generate traffic
        self.logger.info(f"Generating {traffic_type} traffic...")
        try:
            traffic_results = run_traffic_test(net, traffic_type, duration)
        except Exception as e:
            self.logger.error(f"Traffic generation error: {e}", exc_info=True)
            traffic_results = {'error': str(e)}
        
        # Wait for traffic to complete
        self.logger.info(f"Waiting {duration + 5} seconds for traffic to complete...")
        for i in range(duration + 5):
            time.sleep(1)
            if (i + 1) % 5 == 0:
                self.logger.debug(f"{i + 1}/{duration + 5} seconds elapsed")
        
        # Stop monitoring
        monitor.stop()
        
        # Collect results
        self.logger.info("Collecting results...")
        results = {
            'experiment': {
                'routing_scheme': routing_scheme,
                'traffic_type': traffic_type,
                'duration': duration,
                'topology': {
                    'num_spines': self.num_spines,
                    'num_leaves': self.num_leaves,
                    'hosts_per_leaf': self.hosts_per_leaf,
                    'total_hosts': self.num_leaves * self.hosts_per_leaf
                },
                'timestamp': datetime.now().isoformat()
            },
            'traffic': traffic_results,
            'monitoring': monitor.get_statistics()
        }
        
        # Save results
        filename = f"{output_dir}/{routing_scheme}_{traffic_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Results saved to {filename}")
        
        # Print summary
        monitor.print_summary()
        
        # Stop network
        self.logger.info("Stopping network...")
        try:
            if routing_scheme == 'adaptive' and 'router' in locals():
                router.stop()
            net.stop()
        except Exception as e:
            self.logger.warning(f"Warning during cleanup: {e}")
        finally:
            # Ensure cleanup
            import subprocess
            subprocess.call(['sudo', 'mn', '-c'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL)
        
        return results
    
    def run_comparison(self, traffic_type='all_to_all', duration=10, 
                      output_dir='results'):
        """
        Run comparison between ECMP and Adaptive routing.
        
        Args:
            traffic_type: Type of traffic pattern
            duration: Duration of each experiment
            output_dir: Directory to save results
        """
        self.logger.info("="*70)
        self.logger.info("ROUTING COMPARISON EXPERIMENT")
        self.logger.info("="*70)
        self.logger.info(f"Traffic Type: {traffic_type}")
        self.logger.info(f"Duration: {duration} seconds")
        self.logger.info(f"Topology: {self.num_spines} spines, {self.num_leaves} leaves, "
              f"{self.hosts_per_leaf} hosts/leaf")
        self.logger.info("="*70)
        
        results = {}
        
        # Run ECMP experiment
        self.logger.info("Running ECMP Experiment")
        results['ecmp'] = self.run_experiment(
            routing_scheme='ecmp',
            traffic_type=traffic_type,
            duration=duration,
            output_dir=output_dir
        )
        
        # Wait between experiments
        self.logger.info("Waiting 10 seconds before next experiment...")
        time.sleep(10)
        
        # Run Adaptive experiment
        self.logger.info("Running Adaptive Routing Experiment")
        results['adaptive'] = self.run_experiment(
            routing_scheme='adaptive',
            traffic_type=traffic_type,
            duration=duration,
            output_dir=output_dir
        )
        
        # Save comparison results
        comparison_file = f"{output_dir}/comparison_{traffic_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(comparison_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Comparison results saved to {comparison_file}")
        
        # Print comparison summary
        self.print_comparison_summary(results)
        
        return results
    
    def print_comparison_summary(self, results):
        """Print comparison summary"""
        self.logger.info("="*70)
        self.logger.info("COMPARISON SUMMARY")
        self.logger.info("="*70)
        
        ecmp_stats = results['ecmp']['monitoring']
        adaptive_stats = results['adaptive']['monitoring']
        
        self.logger.info("Link Utilization")
        self.logger.info(f"{'Metric':<30} {'ECMP':<20} {'Adaptive':<20}")
        self.logger.info("-" * 70)
        
        # Compare average link utilization
        if ecmp_stats['link_utilization'] and adaptive_stats['link_utilization']:
            ecmp_avg = sum(u['mean'] for u in ecmp_stats['link_utilization'].values()) / len(ecmp_stats['link_utilization'])
            adaptive_avg = sum(u['mean'] for u in adaptive_stats['link_utilization'].values()) / len(adaptive_stats['link_utilization'])
            
            self.logger.info(f"{'Avg Link Utilization (%)':<30} {ecmp_avg:<20.2f} {adaptive_avg:<20.2f}")
            
            ecmp_max = max(u['max'] for u in ecmp_stats['link_utilization'].values())
            adaptive_max = max(u['max'] for u in adaptive_stats['link_utilization'].values())
            
            self.logger.info(f"{'Max Link Utilization (%)':<30} {ecmp_max:<20.2f} {adaptive_max:<20.2f}")
        
        self.logger.info("Packet Drops")
        ecmp_drops = sum(ecmp_stats['packet_drops'].values()) if ecmp_stats['packet_drops'] else 0
        adaptive_drops = sum(adaptive_stats['packet_drops'].values()) if adaptive_stats['packet_drops'] else 0
        
        self.logger.info(f"{'Total Packet Drops':<30} {ecmp_drops:<20} {adaptive_drops:<20}")
        
        self.logger.info("Performance Improvement")
        if ecmp_drops > 0:
            improvement = ((ecmp_drops - adaptive_drops) / ecmp_drops) * 100
            self.logger.info(f"Packet drop reduction: {improvement:.2f}%")
        
        self.logger.info("="*70)


def main():
    parser = argparse.ArgumentParser(
        description='AI Data Center Routing Comparison Experiment'
    )
    
    parser.add_argument('--mode', 
                       choices=['single', 'comparison'],
                       default='comparison',
                       help='Run mode: single experiment or comparison')
    
    parser.add_argument('--routing',
                       choices=['ecmp', 'adaptive'],
                       default='ecmp',
                       help='Routing scheme (for single mode)')
    
    parser.add_argument('--traffic',
                       choices=['all_to_all', 'allreduce', 'bursty'],
                       default='all_to_all',
                       help='Traffic pattern type')
    
    parser.add_argument('--duration',
                       type=int,
                       default=10,
                       help='Experiment duration in seconds')
    
    parser.add_argument('--spines',
                       type=int,
                       default=4,
                       help='Number of spine switches')
    
    parser.add_argument('--leaves',
                       type=int,
                       default=4,
                       help='Number of leaf switches')
    
    parser.add_argument('--hosts',
                       type=int,
                       default=4,
                       help='Number of hosts per leaf')
    
    parser.add_argument('--output',
                       default='results',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Setup logger
    log_level = logging.DEBUG if hasattr(args, 'verbose') and args.verbose else logging.INFO
    setup_logger(level=log_level)
    
    # Create experiment runner
    runner = ExperimentRunner(
        num_spines=args.spines,
        num_leaves=args.leaves,
        hosts_per_leaf=args.hosts
    )
    
    # Run experiment(s)
    if args.mode == 'comparison':
        runner.run_comparison(
            traffic_type=args.traffic,
            duration=args.duration,
            output_dir=args.output
        )
    else:
        runner.run_experiment(
            routing_scheme=args.routing,
            traffic_type=args.traffic,
            duration=args.duration,
            output_dir=args.output
        )


if __name__ == '__main__':
    main()
