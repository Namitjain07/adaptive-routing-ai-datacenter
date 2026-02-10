#!/usr/bin/env python3
"""
AI Traffic Generator for All-to-All Communication Pattern
Simulates synchronized AI training traffic (AllReduce pattern)
"""

import argparse
import time
import json
import threading
from datetime import datetime
import random
import subprocess


class AITrafficGenerator:
    """
    Generate AI training traffic patterns.
    
    Simulates AllReduce collective communication common in
    distributed AI/ML training (e.g., PyTorch DDP, Horovod).
    """
    
    def __init__(self, hosts, traffic_type='all_to_all'):
        """
        Args:
            hosts: List of host objects from Mininet
            traffic_type: 'all_to_all', 'allreduce', or 'parameter_server'
        """
        self.hosts = hosts
        self.traffic_type = traffic_type
        self.results = []
        self.servers = {}
        self.host_locks = {}  # Thread locks for each host
        for host in hosts:
            self.host_locks[host.name] = threading.Lock()
        
    def setup_iperf_servers(self, port=5001):
        """Start iperf3 servers on all hosts"""
        print("*** Starting iperf3 servers on all hosts...")
        
        for host in self.hosts:
            # Kill any existing iperf3 processes
            host.cmd('pkill -9 iperf3')
            
            # Start iperf3 server in background
            server_port = port
            host.cmd(f'iperf3 -s -p {server_port} -D > /dev/null 2>&1')
            self.servers[host.name] = server_port
            print(f"  Server started on {host.name}:{server_port}")
        
        # Wait for servers to start
        time.sleep(2)
    
    def cleanup_servers(self):
        """Stop all iperf3 servers"""
        print("*** Stopping iperf3 servers...")
        for host in self.hosts:
            host.cmd('pkill -9 iperf3')
    
    def generate_all_to_all(self, duration=10, bandwidth='100M', 
                           protocol='tcp', parallel=1):
        """
        Generate all-to-all traffic pattern.
        Each host sends to every other host simultaneously.
        
        Args:
            duration: Traffic duration in seconds
            bandwidth: Target bandwidth per flow (e.g., '100M')
            protocol: 'tcp' or 'udp'
            parallel: Number of parallel streams per flow
        """
        print(f"\n*** Generating all-to-all traffic pattern")
        print(f"    Duration: {duration}s, Bandwidth: {bandwidth}, Protocol: {protocol}")
        
        self.setup_iperf_servers()
        
        results = []
        threads = []
        
        # Each host sends to all other hosts
        for src_host in self.hosts:
            for dst_host in self.hosts:
                if src_host == dst_host:
                    continue
                
                # Create thread for this flow
                thread = threading.Thread(
                    target=self._run_iperf_client,
                    args=(src_host, dst_host, duration, bandwidth, 
                          protocol, parallel, results)
                )
                threads.append(thread)
        
        # Start all flows simultaneously (synchronized start)
        print(f"*** Starting {len(threads)} flows simultaneously...")
        start_time = time.time()
        
        for thread in threads:
            thread.start()
        
        # Wait for all flows to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"*** All flows completed in {total_time:.2f}s")
        
        self.cleanup_servers()
        self.results = results
        
        return results
    
    def _run_iperf_client(self, src_host, dst_host, duration, bandwidth,
                         protocol, parallel, results):
        """Run iperf3 client (single flow)"""
        dst_ip = dst_host.IP()
        dst_port = self.servers.get(dst_host.name, 5001)
        
        # Build iperf3 command
        cmd = f'iperf3 -c {dst_ip} -p {dst_port} -t {duration}'
        
        if protocol == 'udp':
            cmd += f' -u -b {bandwidth}'
        else:
            cmd += f' -b {bandwidth}'
        
        if parallel > 1:
            cmd += f' -P {parallel}'
        
        cmd += ' -J'  # JSON output
        
        # Run iperf3 client with thread lock to prevent concurrent access
        start_time = time.time()
        with self.host_locks[src_host.name]:
            output = src_host.cmd(cmd)
        end_time = time.time()
        flow_completion_time = end_time - start_time
        
        # Parse results
        try:
            result = json.loads(output)
            
            flow_info = {
                'src': src_host.name,
                'src_ip': src_host.IP(),
                'dst': dst_host.name,
                'dst_ip': dst_ip,
                'protocol': protocol,
                'duration': duration,
                'flow_completion_time': flow_completion_time,
                'timestamp': datetime.now().isoformat()
            }
            
            if 'end' in result:
                end_stats = result['end']
                
                if 'sum_sent' in end_stats:
                    flow_info['bytes_sent'] = end_stats['sum_sent']['bytes']
                    flow_info['bps_sent'] = end_stats['sum_sent']['bits_per_second']
                
                if 'sum_received' in end_stats:
                    flow_info['bytes_received'] = end_stats['sum_received']['bytes']
                    flow_info['bps_received'] = end_stats['sum_received']['bits_per_second']
                
                # Get stream stats for latency/jitter
                if 'streams' in result and len(result['streams']) > 0:
                    stream = result['streams'][0]
                    if 'udp' in stream:
                        udp_stats = stream['udp']
                        flow_info['jitter_ms'] = udp_stats.get('jitter_ms', 0)
                        flow_info['lost_packets'] = udp_stats.get('lost_packets', 0)
                        flow_info['lost_percent'] = udp_stats.get('lost_percent', 0)
            
            results.append(flow_info)
            
        except json.JSONDecodeError:
            print(f"Warning: Failed to parse iperf3 output for {src_host.name} -> {dst_host.name}")
        except Exception as e:
            print(f"Error processing flow {src_host.name} -> {dst_host.name}: {e}")
    
    def generate_allreduce_pattern(self, duration=10, message_size='1M',
                                   num_iterations=10):
        """
        Simulate AllReduce collective operation.
        
        AllReduce: All hosts exchange gradients and compute global average.
        Pattern: Ring-AllReduce or Tree-AllReduce
        
        Args:
            duration: Total duration
            message_size: Size of message per iteration
            num_iterations: Number of AllReduce iterations
        """
        print(f"\n*** Simulating AllReduce pattern")
        print(f"    Iterations: {num_iterations}, Message size: {message_size}")
        
        # Ring-AllReduce: each host sends to next in ring
        num_hosts = len(self.hosts)
        results = []
        
        for iteration in range(num_iterations):
            print(f"  Iteration {iteration + 1}/{num_iterations}")
            
            # Scatter-Reduce phase
            for step in range(num_hosts - 1):
                threads = []
                for i, host in enumerate(self.hosts):
                    next_idx = (i + 1) % num_hosts
                    next_host = self.hosts[next_idx]
                    
                    thread = threading.Thread(
                        target=self._send_chunk,
                        args=(host, next_host, message_size, results)
                    )
                    threads.append(thread)
                    thread.start()
                
                for thread in threads:
                    thread.join()
            
            # AllGather phase
            for step in range(num_hosts - 1):
                threads = []
                for i, host in enumerate(self.hosts):
                    next_idx = (i + 1) % num_hosts
                    next_host = self.hosts[next_idx]
                    
                    thread = threading.Thread(
                        target=self._send_chunk,
                        args=(host, next_host, message_size, results)
                    )
                    threads.append(thread)
                    thread.start()
                
                for thread in threads:
                    thread.join()
        
        self.results = results
        return results
    
    def _send_chunk(self, src_host, dst_host, size, results):
        """Send a data chunk between hosts"""
        # Use netcat for simple data transfer
        dst_ip = dst_host.IP()
        port = 9999 + random.randint(0, 100)
        
        # Start receiver
        dst_host.cmd(f'nc -l {port} > /dev/null &')
        time.sleep(0.1)
        
        # Send data
        start = time.time()
        src_host.cmd(f'dd if=/dev/zero bs={size} count=1 2>/dev/null | nc {dst_ip} {port}')
        latency = time.time() - start
        
        results.append({
            'src': src_host.name,
            'dst': dst_host.name,
            'latency': latency,
            'timestamp': datetime.now().isoformat()
        })
    
    def generate_bursty_traffic(self, duration=10, burst_size='100M',
                               idle_time=0.1, bandwidth='1G'):
        """
        Generate bursty traffic pattern (common in AI inference).
        
        Args:
            duration: Total duration
            burst_size: Size of each burst
            idle_time: Idle time between bursts (seconds)
            bandwidth: Peak bandwidth during burst
        """
        print(f"\n*** Generating bursty traffic pattern")
        print(f"    Duration: {duration}s, Burst: {burst_size}, Idle: {idle_time}s")
        
        self.setup_iperf_servers()
        
        start_time = time.time()
        results = []
        
        while time.time() - start_time < duration:
            # Burst phase - all-to-all traffic
            threads = []
            for src_host in self.hosts:
                for dst_host in self.hosts:
                    if src_host == dst_host:
                        continue
                    
                    thread = threading.Thread(
                        target=self._run_burst,
                        args=(src_host, dst_host, burst_size, bandwidth, results)
                    )
                    threads.append(thread)
                    thread.start()
            
            for thread in threads:
                thread.join()
            
            # Idle phase
            time.sleep(idle_time)
        
        self.cleanup_servers()
        self.results = results
        
        return results
    
    def _run_burst(self, src_host, dst_host, size, bandwidth, results):
        """Run a single burst"""
        dst_ip = dst_host.IP()
        dst_port = self.servers.get(dst_host.name, 5001)
        
        # Calculate duration for burst size at given bandwidth
        # Size in bytes, bandwidth in bps
        burst_duration = 1  # seconds (simplified)
        
        cmd = f'iperf3 -c {dst_ip} -p {dst_port} -t {burst_duration} -b {bandwidth} -J'
        
        output = src_host.cmd(cmd)
        
        try:
            result = json.loads(output)
            if 'end' in result and 'sum_received' in result['end']:
                results.append({
                    'src': src_host.name,
                    'dst': dst_host.name,
                    'bytes': result['end']['sum_received']['bytes'],
                    'bps': result['end']['sum_received']['bits_per_second'],
                    'timestamp': datetime.now().isoformat()
                })
        except:
            pass
    
    def save_results(self, filename):
        """Save traffic results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"*** Results saved to {filename}")


def run_traffic_test(net, traffic_type='all_to_all', duration=10):
    """
    Run traffic test on Mininet network.
    
    Args:
        net: Mininet network object
        traffic_type: Type of traffic pattern
        duration: Duration in seconds
    """
    hosts = net.hosts
    
    generator = AITrafficGenerator(hosts, traffic_type)
    
    if traffic_type == 'all_to_all':
        results = generator.generate_all_to_all(
            duration=duration,
            bandwidth='100M',
            protocol='tcp',
            parallel=1
        )
    elif traffic_type == 'allreduce':
        results = generator.generate_allreduce_pattern(
            duration=duration,
            message_size='10M',
            num_iterations=5
        )
    elif traffic_type == 'bursty':
        results = generator.generate_bursty_traffic(
            duration=duration,
            burst_size='100M',
            idle_time=0.1
        )
    else:
        print(f"Unknown traffic type: {traffic_type}")
        return None
    
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AI Traffic Generator')
    parser.add_argument('--type', default='all_to_all',
                       choices=['all_to_all', 'allreduce', 'bursty'],
                       help='Traffic pattern type')
    parser.add_argument('--duration', type=int, default=10,
                       help='Duration in seconds')
    
    args = parser.parse_args()
    
    print("AI Traffic Generator")
    print(f"Use with Mininet network for {args.type} traffic")
