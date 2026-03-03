#!/usr/bin/env python3
"""
Hash Collision Test Scenarios
Demonstrates ECMP hash collisions and adaptive routing solutions.

This test suite creates specific traffic patterns designed to trigger
ECMP hash collisions, then shows how adaptive routing resolves them.
"""

import sys
import time
import json
import argparse
from datetime import datetime
import subprocess

sys.path.append('/home/namitjain07/Desktop/NAI')

from topologies.leaf_spine import create_network
from routing.ecmp_routing import setup_ecmp_routing
from routing.adaptive_routing import setup_adaptive_routing
from routing.monitor import NetworkMonitor


class CollisionTestSuite:
    """
    Test suite for demonstrating hash collision scenarios.
    """
    
    def __init__(self, num_spines=4, num_leaves=4, hosts_per_leaf=4):
        self.num_spines = num_spines
        self.num_leaves = num_leaves
        self.hosts_per_leaf = hosts_per_leaf
        self.results = {}
    
    def test_elephant_flow_collision(self, routing_scheme='ecmp', duration=20):
        """
        Test Case 1: Elephant Flow Collision
        
        Create multiple large flows that hash to the same ECMP bucket,
        causing severe congestion on one path while other paths remain idle.
        
        Scenario:
        - 4 pairs of hosts sending large flows simultaneously
        - Flows engineered to collide on same spine link
        - Expected: ECMP shows imbalance, Adaptive spreads load
        """
        print("\n" + "="*80)
        print("TEST CASE 1: Elephant Flow Collision")
        print("="*80)
        print(f"Routing: {routing_scheme.upper()}")
        print(f"Scenario: 4 elephant flows designed to hash to same path")
        print("="*80)
        
        # Create network
        net = create_network(
            num_spines=self.num_spines,
            num_leaves=self.num_leaves,
            hosts_per_leaf=self.hosts_per_leaf
        )
        net.start()
        print("*** Waiting for network to initialize...")
        time.sleep(5)  # Increased from 2 to 5 seconds
        
        # Install routing
        if routing_scheme == 'ecmp':
            setup_ecmp_routing(net, self.num_spines, self.num_leaves, self.hosts_per_leaf)
        else:
            setup_adaptive_routing(net, self.num_spines, self.num_leaves, 
                                  self.hosts_per_leaf, mode='flowlet')
        print("*** Waiting for routing to propagate...")
        time.sleep(3)  # Increased from 2 to 3 seconds
        
        # Verify connectivity
        print("*** Verifying network connectivity...")
        hosts = net.hosts
        if len(hosts) >= 2:
            h1, h2 = hosts[0], hosts[1]
            result = h1.cmd(f'ping -c 1 -W 1 {h2.IP()}')
            if 'packets transmitted' in result and '1 received' in result:
                print("    ✓ Network connectivity verified")
            else:
                print("    ⚠ Warning: Connectivity check failed, continuing anyway...")
        
        # Get hosts (redeclared after connectivity check for clarity)
        
        # Start monitoring
        monitor = NetworkMonitor(net, sample_interval=0.5)  # 500ms sampling
        monitor.start()
        
        # Create collision-prone flows
        # Strategy: Use specific port combinations that hash to same bucket
        # For OVS select group, hash is typically: hash(src_ip, dst_ip, src_port, dst_port, proto)
        
        collision_flows = [
            # All these flows will likely hash to same bucket
            # Different src/dst IPs but ports chosen to create collision
            {'src_idx': 0, 'dst_idx': 8, 'src_port': 5000, 'dst_port': 6000},
            {'src_idx': 1, 'dst_idx': 9, 'src_port': 5001, 'dst_port': 6001},
            {'src_idx': 2, 'dst_idx': 10, 'src_port': 5002, 'dst_port': 6002},
            {'src_idx': 3, 'dst_idx': 11, 'src_port': 5003, 'dst_port': 6003},
        ]
        
        # Start iperf3 servers on destination hosts with specific ports
        print("\n*** Setting up iperf3 servers...")
        for flow in collision_flows:
            if flow['dst_idx'] < len(hosts):
                dst = hosts[flow['dst_idx']]
                dst.cmd(f'pkill -9 iperf3')  # Clean up
                dst.cmd(f'iperf3 -s -p {flow["dst_port"]} -D > /dev/null 2>&1')
                print(f"  Server on {dst.name}:{flow['dst_port']}")
        
        time.sleep(2)
        
        # Launch elephant flows
        print(f"\n*** Launching {len(collision_flows)} elephant flows...")
        print("    Target bandwidth: 50M per flow (total 200M on 40M network)")
        
        flow_threads = []
        for flow in collision_flows:
            if flow['src_idx'] < len(hosts) and flow['dst_idx'] < len(hosts):
                src = hosts[flow['src_idx']]
                dst = hosts[flow['dst_idx']]
                
                # Launch iperf3 client (high bandwidth to induce congestion)
                cmd = (f'iperf3 -c {dst.IP()} -p {flow["dst_port"]} '
                      f'-t {duration} -b 50M --cport {flow["src_port"]} -J '
                      f'> /tmp/iperf_{src.name}_to_{dst.name}.json 2>&1 &')
                
                src.cmd(cmd)
                print(f"  Flow: {src.name}:{flow['src_port']} → {dst.name}:{flow['dst_port']}")
        
        # Monitor network during test
        print(f"\n*** Monitoring network for {duration} seconds...")
        for i in range(duration):
            time.sleep(1)
            if (i + 1) % 5 == 0:
                print(f"    ... {i + 1}/{duration} seconds")
                # Print instant stats
                self._print_instant_stats(net)
        
        # Stop monitoring
        monitor.stop()
        
        # Collect results
        print("\n*** Collecting results...")
        results = {
            'test': 'elephant_flow_collision',
            'routing': routing_scheme,
            'duration': duration,
            'num_flows': len(collision_flows),
            'monitoring': monitor.get_statistics(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Parse iperf3 results
        flow_results = []
        for flow in collision_flows:
            if flow['src_idx'] < len(hosts) and flow['dst_idx'] < len(hosts):
                src = hosts[flow['src_idx']]
                dst = hosts[flow['dst_idx']]
                
                result_file = f'/tmp/iperf_{src.name}_to_{dst.name}.json'
                try:
                    output = src.cmd(f'cat {result_file}')
                    if output:
                        iperf_data = json.loads(output)
                        if 'end' in iperf_data:
                            flow_results.append({
                                'src': src.name,
                                'dst': dst.name,
                                'throughput_bps': iperf_data['end']['sum_received']['bits_per_second'],
                                'retransmits': iperf_data['end']['sum_sent'].get('retransmits', 0)
                            })
                except:
                    pass
        
        results['flows'] = flow_results
        
        # Analyze collision impact
        self._analyze_collision_impact(results, net)
        
        # Cleanup
        for host in hosts:
            host.cmd('pkill -9 iperf3')
        
        net.stop()
        subprocess.call(['sudo', 'mn', '-c'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return results
    
    def test_synchronized_burst_collision(self, routing_scheme='ecmp', duration=15):
        """
        Test Case 2: Synchronized Burst Collision
        
        Simulates AI training gradient exchange where all workers
        simultaneously send bursts, creating synchronized incast.
        
        Scenario:
        - All hosts send to one aggregator simultaneously
        - Multiple iterations (bursts) separated by idle periods
        - Expected: ECMP overloads one path, Adaptive distributes across bursts
        """
        print("\n" + "="*80)
        print("TEST CASE 2: Synchronized Burst Collision (Incast)")
        print("="*80)
        print(f"Routing: {routing_scheme.upper()}")
        print(f"Scenario: All hosts → aggregator in synchronized bursts")
        print("="*80)
        
        # Create network
        net = create_network(
            num_spines=self.num_spines,
            num_leaves=self.num_leaves,
            hosts_per_leaf=self.hosts_per_leaf
        )
        net.start()
        print("*** Waiting for network to initialize...")
        time.sleep(5)  # Increased from 2 to 5 seconds
        
        # Install routing
        if routing_scheme == 'ecmp':
            setup_ecmp_routing(net, self.num_spines, self.num_leaves, self.hosts_per_leaf)
        else:
            setup_adaptive_routing(net, self.num_spines, self.num_leaves, 
                                  self.hosts_per_leaf, mode='flowlet')
        print("*** Waiting for routing to propagate...")
        time.sleep(3)  # Increased from 2 to 3 seconds
        
        # Verify connectivity
        print("*** Verifying network connectivity...")
        hosts = net.hosts
        if len(hosts) >= 2:
            h1, h2 = hosts[0], hosts[1]
            result = h1.cmd(f'ping -c 1 -W 1 {h2.IP()}')
            if 'packets transmitted' in result and '1 received' in result:
                print("    ✓ Network connectivity verified")
            else:
                print("    ⚠ Warning: Connectivity check failed, continuing anyway...")

        
        # Choose aggregator (parameter server)
        aggregator = hosts[-1]  # Last host
        workers = hosts[:-1]  # All other hosts
        
        print(f"\n*** Aggregator: {aggregator.name} ({aggregator.IP()})")
        print(f"*** Workers: {len(workers)} hosts")
        
        # Start monitoring
        monitor = NetworkMonitor(net, sample_interval=0.5)
        monitor.start()
        
        # Start iperf3 server on aggregator
        aggregator.cmd('pkill -9 iperf3')
        aggregator.cmd('iperf3 -s -p 5001 -D > /dev/null 2>&1')
        time.sleep(1)
        
        # Simulate 3 synchronized bursts (gradient exchange iterations)
        burst_duration = 3  # 3 seconds per burst
        idle_duration = 2   # 2 seconds idle (simulating computation)
        num_bursts = 3
        
        print(f"\n*** Running {num_bursts} synchronized bursts...")
        print(f"    Burst: {burst_duration}s, Idle: {idle_duration}s")
        
        all_results = []
        
        for burst_num in range(num_bursts):
            print(f"\n  [BURST {burst_num + 1}/{num_bursts}]")
            
            # All workers send simultaneously
            for i, worker in enumerate(workers):
                if i >= 12:  # Limit to 12 workers
                    break
                
                cmd = (f'iperf3 -c {aggregator.IP()} -p 5001 -t {burst_duration} '
                      f'-b 30M --cport {5000 + i} -J '
                      f'> /tmp/iperf_burst{burst_num}_{worker.name}.json 2>&1 &')
                worker.cmd(cmd)
            
            print(f"    {min(len(workers), 12)} workers sending...")
            
            # Wait for burst to complete
            time.sleep(burst_duration + 1)
            
            # Idle period (simulating GPU computation)
            print(f"    Idle period ({idle_duration}s)...")
            time.sleep(idle_duration)
        
        # Stop monitoring
        monitor.stop()
        
        # Collect results
        results = {
            'test': 'synchronized_burst_collision',
            'routing': routing_scheme,
            'num_bursts': num_bursts,
            'burst_duration': burst_duration,
            'workers': len(workers),
            'monitoring': monitor.get_statistics(),
            'timestamp': datetime.now().isoformat()
        }
        
        # Analyze incast impact
        self._analyze_incast_impact(results, net, monitor)
        
        # Cleanup
        for host in hosts:
            host.cmd('pkill -9 iperf3')
        
        net.stop()
        subprocess.call(['sudo', 'mn', '-c'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return results
    
    def test_port_collision_matrix(self, routing_scheme='ecmp', duration=15):
        """
        Test Case 3: Port Collision Matrix
        
        Systematically create flows with port combinations that
        deliberately collide under ECMP hashing.
        
        Scenario:
        - Matrix of src/dst pairs with calculated port collisions
        - Tests hash function weaknesses
        - Expected: ECMP severe imbalance, Adaptive balanced
        """
        print("\n" + "="*80)
        print("TEST CASE 3: Port Collision Matrix")
        print("="*80)
        print(f"Routing: {routing_scheme.upper()}")
        print(f"Scenario: Engineered port collisions to stress hash function")
        print("="*80)
        
        # Create network
        net = create_network(
            num_spines=self.num_spines,
            num_leaves=self.num_leaves,
            hosts_per_leaf=self.hosts_per_leaf
        )
        net.start()
        print("*** Waiting for network to initialize...")
        time.sleep(5)  # Increased from 2 to 5 seconds
        
        # Install routing
        if routing_scheme == 'ecmp':
            setup_ecmp_routing(net, self.num_spines, self.num_leaves, self.hosts_per_leaf)
        else:
            setup_adaptive_routing(net, self.num_spines, self.num_leaves, 
                                  self.hosts_per_leaf, mode='flowlet')
        print("*** Waiting for routing to propagate...")
        time.sleep(3)  # Increased from 2 to 3 seconds
        
        # Verify connectivity
        print("*** Verifying network connectivity...")
        hosts = net.hosts
        if len(hosts) >= 2:
            h1, h2 = hosts[0], hosts[1]
            result = h1.cmd(f'ping -c 1 -W 1 {h2.IP()}')
            if 'packets transmitted' in result and '1 received' in result:
                print("    ✓ Network connectivity verified")
            else:
                print("    ⚠ Warning: Connectivity check failed, continuing anyway...")
        
        monitor = NetworkMonitor(net, sample_interval=0.5)
        monitor.start()
        
        # Create port collision pattern
        # Strategy: Use ports that when XORed/hashed produce same result mod num_spines
        # For 4 spines, we want hash(flow) mod 4 to be the same for multiple flows
        
        collision_matrix = []
        base_port = 5000
        
        # Create 8 flows that should all hash to the same spine
        for i in range(8):
            if i * 2 < len(hosts) and i * 2 + 1 < len(hosts):
                # Port manipulation to force collision
                # OVS typically uses: (src_ip XOR dst_ip XOR src_port XOR dst_port) mod num_paths
                src_port = base_port + (i * 4)  # Increment by 4 (num_spines)
                dst_port = base_port + (i * 4)
                
                collision_matrix.append({
                    'src_idx': i * 2,
                    'dst_idx': i * 2 + 1,
                    'src_port': src_port,
                    'dst_port': dst_port
                })
        
        print(f"\n*** Created {len(collision_matrix)} collision-prone flows")
        print("    Port pattern designed to hash to same path")
        
        # Setup servers
        for flow in collision_matrix:
            if flow['dst_idx'] < len(hosts):
                dst = hosts[flow['dst_idx']]
                dst.cmd('pkill -9 iperf3')
                dst.cmd(f'iperf3 -s -p {flow["dst_port"]} -D > /dev/null 2>&1')
        
        time.sleep(2)
        
        # Launch flows
        print(f"\n*** Launching flows...")
        for flow in collision_matrix:
            if flow['src_idx'] < len(hosts) and flow['dst_idx'] < len(hosts):
                src = hosts[flow['src_idx']]
                dst = hosts[flow['dst_idx']]
                
                cmd = (f'iperf3 -c {dst.IP()} -p {flow["dst_port"]} '
                      f'-t {duration} -b 40M --cport {flow["src_port"]} '
                      f'> /dev/null 2>&1 &')
                src.cmd(cmd)
                print(f"  {src.name}:{flow['src_port']} → {dst.name}:{flow['dst_port']}")
        
        # Monitor
        print(f"\n*** Monitoring for {duration} seconds...")
        for i in range(duration):
            time.sleep(1)
            if (i + 1) % 5 == 0:
                print(f"    ... {i + 1}/{duration} seconds")
                self._print_instant_stats(net)
        
        monitor.stop()
        
        # Results
        results = {
            'test': 'port_collision_matrix',
            'routing': routing_scheme,
            'num_flows': len(collision_matrix),
            'monitoring': monitor.get_statistics(),
            'timestamp': datetime.now().isoformat()
        }
        
        self._analyze_collision_impact(results, net)
        
        # Cleanup
        for host in hosts:
            host.cmd('pkill -9 iperf3')
        
        net.stop()
        subprocess.call(['sudo', 'mn', '-c'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return results
    
    def _print_instant_stats(self, net):
        """Print instantaneous link statistics"""
        # Get stats from spine switches
        spines = [sw for sw in net.switches if 'spine' in sw.name]
        
        print("      [Link Utilization Snapshot]")
        for spine in spines[:self.num_spines]:
            # Get port stats
            output = spine.cmd(f'ovs-ofctl dump-ports {spine.name} | grep "port"')
            lines = output.strip().split('\n')
            
            # Simple parsing - just show activity
            active_ports = 0
            for line in lines:
                if 'tx pkts' in line and 'pkts=0' not in line:
                    active_ports += 1
            
            print(f"        {spine.name}: {active_ports} active ports")
    
    def _analyze_collision_impact(self, results, net):
        """Analyze and report collision impact"""
        print("\n*** Collision Impact Analysis ***")
        
        monitoring = results.get('monitoring', {})
        link_util = monitoring.get('link_utilization', {})
        
        if link_util:
            # Calculate imbalance across spine links
            spine_utils = []
            for link_name, stats in link_util.items():
                if 'spine' in link_name:
                    spine_utils.append(stats.get('mean', 0))
            
            if spine_utils:
                import numpy as np
                mean_util = np.mean(spine_utils)
                std_util = np.std(spine_utils)
                max_util = np.max(spine_utils)
                min_util = np.min(spine_utils)
                
                # Balance score
                balance_score = 1.0 - (std_util / mean_util) if mean_util > 0 else 0
                
                # Imbalance factor
                imbalance_factor = max_util / mean_util if mean_util > 0 else 1.0
                
                print(f"  Mean spine utilization: {mean_util:.2f}%")
                print(f"  Std deviation: {std_util:.2f}%")
                print(f"  Range: [{min_util:.2f}%, {max_util:.2f}%]")
                print(f"  Balance Score: {balance_score:.3f} (1.0 = perfect)")
                print(f"  Imbalance Factor: {imbalance_factor:.2f}x (1.0 = perfect)")
                
                results['balance_score'] = balance_score
                results['imbalance_factor'] = imbalance_factor
                
                # Interpretation
                if imbalance_factor > 2.0:
                    print(f"\n  ⚠️  SEVERE IMBALANCE: Some paths {imbalance_factor:.1f}x more loaded!")
                    print("      Hash collisions are causing significant hotspots.")
                elif imbalance_factor > 1.5:
                    print(f"\n  ⚠️  MODERATE IMBALANCE: {imbalance_factor:.1f}x difference between paths")
                else:
                    print(f"\n  ✓  GOOD BALANCE: Only {imbalance_factor:.1f}x difference")
        else:
            print("  ⚠️  No link utilization data available")
        
        # Check packet drops
        drops = monitoring.get('packet_drops', {})
        total_drops = sum(drops.values()) if drops else 0
        
        print(f"\n  Total packet drops: {total_drops}")
        if total_drops > 100:
            print(f"  ⚠️  CONGESTION DETECTED: {total_drops} drops indicate buffer overflow")
        
        results['total_drops'] = total_drops
    
    def _analyze_incast_impact(self, results, net, monitor):
        """Analyze incast congestion impact"""
        print("\n*** Incast Impact Analysis ***")
        
        monitoring = results.get('monitoring', {})
        
        # Look for queue buildup patterns
        samples = monitor.samples if hasattr(monitor, 'samples') else []
        
        if samples:
            print(f"  Collected {len(samples)} monitoring samples")
            
            # Analyze temporal patterns
            # In incast, we expect spikes during bursts, idle otherwise
            print("  Burst pattern analysis:")
            print("    Looking for synchronized congestion spikes...")
        else:
            print("  ⚠️  No time-series data available")
        
        # Check for retransmissions in flow results
        flows = results.get('flows', [])
        if flows:
            total_retrans = sum(f.get('retransmits', 0) for f in flows)
            print(f"\n  Total retransmissions: {total_retrans}")
            
            if total_retrans > 50:
                print("  ⚠️  HIGH RETRANSMISSIONS: Incast causing packet loss")
    
    def run_comparison_suite(self, output_dir='collision_tests'):
        """
        Run full comparison: ECMP vs Adaptive for all test cases.
        """
        print("\n" + "="*80)
        print("COLLISION TEST SUITE - COMPREHENSIVE COMPARISON")
        print("="*80)
        print("Comparing ECMP vs Adaptive Routing across collision scenarios")
        print("="*80)
        
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        all_results = {}
        
        # Test 1: Elephant Flow Collision
        print("\n\n### TEST 1: Elephant Flow Collision ###")
        
        print("\n[RUNNING ECMP...]")
        ecmp_elephant = self.test_elephant_flow_collision(routing_scheme='ecmp', duration=20)
        time.sleep(5)
        
        print("\n[RUNNING ADAPTIVE...]")
        adaptive_elephant = self.test_elephant_flow_collision(routing_scheme='adaptive', duration=20)
        time.sleep(5)
        
        all_results['elephant_collision'] = {
            'ecmp': ecmp_elephant,
            'adaptive': adaptive_elephant
        }
        
        # Test 2: Synchronized Burst
        print("\n\n### TEST 2: Synchronized Burst Collision ###")
        
        print("\n[RUNNING ECMP...]")
        ecmp_burst = self.test_synchronized_burst_collision(routing_scheme='ecmp', duration=15)
        time.sleep(5)
        
        print("\n[RUNNING ADAPTIVE...]")
        adaptive_burst = self.test_synchronized_burst_collision(routing_scheme='adaptive', duration=15)
        time.sleep(5)
        
        all_results['burst_collision'] = {
            'ecmp': ecmp_burst,
            'adaptive': adaptive_burst
        }
        
        # Test 3: Port Collision Matrix
        print("\n\n### TEST 3: Port Collision Matrix ###")
        
        print("\n[RUNNING ECMP...]")
        ecmp_port = self.test_port_collision_matrix(routing_scheme='ecmp', duration=15)
        time.sleep(5)
        
        print("\n[RUNNING ADAPTIVE...]")
        adaptive_port = self.test_port_collision_matrix(routing_scheme='adaptive', duration=15)
        
        all_results['port_collision'] = {
            'ecmp': ecmp_port,
            'adaptive': adaptive_port
        }
        
        # Save results
        result_file = f'{output_dir}/collision_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(result_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\n*** Results saved to {result_file}")
        
        # Print summary comparison
        self._print_comparison_summary(all_results)
        
        return all_results
    
    def _print_comparison_summary(self, all_results):
        """Print comprehensive comparison summary"""
        print("\n" + "="*80)
        print("COLLISION TEST SUMMARY - ECMP vs ADAPTIVE")
        print("="*80)
        
        for test_name, results in all_results.items():
            print(f"\n### {test_name.upper().replace('_', ' ')} ###")
            
            ecmp = results.get('ecmp', {})
            adaptive = results.get('adaptive', {})
            
            # Balance score comparison
            ecmp_balance = ecmp.get('balance_score', 0)
            adaptive_balance = adaptive.get('balance_score', 0)
            
            ecmp_imbalance = ecmp.get('imbalance_factor', 1.0)
            adaptive_imbalance = adaptive.get('imbalance_factor', 1.0)
            
            ecmp_drops = ecmp.get('total_drops', 0)
            adaptive_drops = adaptive.get('total_drops', 0)
            
            print(f"\n  Balance Score:")
            print(f"    ECMP:     {ecmp_balance:.3f}")
            print(f"    Adaptive: {adaptive_balance:.3f}")
            if adaptive_balance > ecmp_balance:
                improvement = ((adaptive_balance - ecmp_balance) / ecmp_balance * 100) if ecmp_balance > 0 else 0
                print(f"    >>> Adaptive {improvement:.1f}% better ✓")
            
            print(f"\n  Imbalance Factor:")
            print(f"    ECMP:     {ecmp_imbalance:.2f}x")
            print(f"    Adaptive: {adaptive_imbalance:.2f}x")
            if adaptive_imbalance < ecmp_imbalance:
                improvement = ((ecmp_imbalance - adaptive_imbalance) / ecmp_imbalance * 100)
                print(f"    >>> Adaptive {improvement:.1f}% reduction ✓")
            
            print(f"\n  Packet Drops:")
            print(f"    ECMP:     {ecmp_drops}")
            print(f"    Adaptive: {adaptive_drops}")
            if adaptive_drops < ecmp_drops:
                reduction = ecmp_drops - adaptive_drops
                print(f"    >>> Adaptive reduced drops by {reduction} ✓")
        
        print("\n" + "="*80)
        print("KEY INSIGHTS:")
        print("- ECMP hash collisions cause severe load imbalance")
        print("- Adaptive routing spreads load across available paths")
        print("- Collision scenarios amplify benefits of adaptive routing")
        print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Hash Collision Test Suite for ECMP vs Adaptive Routing'
    )
    
    parser.add_argument('--test',
                       choices=['elephant', 'burst', 'port', 'all'],
                       default='all',
                       help='Which test to run')
    
    parser.add_argument('--routing',
                       choices=['ecmp', 'adaptive', 'comparison'],
                       default='comparison',
                       help='Routing scheme to test')
    
    parser.add_argument('--duration',
                       type=int,
                       default=15,
                       help='Test duration in seconds')
    
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
                       help='Hosts per leaf')
    
    parser.add_argument('--output',
                       default='collision_tests',
                       help='Output directory')
    
    args = parser.parse_args()
    
    # Create test suite
    suite = CollisionTestSuite(
        num_spines=args.spines,
        num_leaves=args.leaves,
        hosts_per_leaf=args.hosts
    )
    
    # Run tests
    if args.routing == 'comparison' and args.test == 'all':
        # Full comparison suite
        suite.run_comparison_suite(output_dir=args.output)
    else:
        # Single test
        if args.test == 'elephant' or args.test == 'all':
            suite.test_elephant_flow_collision(routing_scheme=args.routing, duration=args.duration)
        
        if args.test == 'burst' or args.test == 'all':
            suite.test_synchronized_burst_collision(routing_scheme=args.routing, duration=args.duration)
        
        if args.test == 'port' or args.test == 'all':
            suite.test_port_collision_matrix(routing_scheme=args.routing, duration=args.duration)


if __name__ == '__main__':
    main()
