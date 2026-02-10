#!/usr/bin/env python3
"""
Network Monitoring and Measurement Tools
Collect metrics for routing comparison.
"""

import time
import json
import threading
from datetime import datetime
from collections import defaultdict
import subprocess
import re


class NetworkMonitor:
    """
    Monitor network statistics during experiments.
    
    Collects:
    - Link utilization
    - Queue lengths
    - Packet drops
    - Flow completion times
    - Tail latency
    """
    
    def __init__(self, net, sample_interval=1.0):
        """
        Args:
            net: Mininet network object
            sample_interval: Sampling interval in seconds
        """
        self.net = net
        self.sample_interval = sample_interval
        self.monitoring = False
        self.monitor_thread = None
        self.samples = []
        self.link_stats = defaultdict(list)
        self.flow_stats = defaultdict(dict)
        
    def start(self):
        """Start monitoring in background thread"""
        self.monitoring = True
        self.samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        print("*** Network monitoring started")
    
    def stop(self):
        """Stop monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("*** Network monitoring stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            sample = self._collect_sample()
            self.samples.append(sample)
            time.sleep(self.sample_interval)
    
    def _collect_sample(self):
        """Collect one sample of network statistics"""
        sample = {
            'timestamp': datetime.now().isoformat(),
            'switches': {},
            'links': {}
        }
        
        for switch in self.net.switches:
            switch_stats = self._get_switch_stats(switch)
            sample['switches'][switch.name] = switch_stats
        
        return sample
    
    def _get_switch_stats(self, switch):
        """Get statistics from a single switch"""
        stats = {
            'ports': {},
            'flows': {},
            'queues': {}
        }
        
        # Get port statistics
        try:
            output = switch.cmd(f'ovs-ofctl dump-ports {switch.name}')
            stats['ports'] = self._parse_port_stats(output)
        except:
            pass
        
        # Get flow statistics
        try:
            output = switch.cmd(f'ovs-ofctl dump-flows {switch.name}')
            stats['flows'] = self._parse_flow_stats(output)
        except:
            pass
        
        # Get queue statistics
        try:
            output = switch.cmd(f'ovs-ofctl queue-stats {switch.name}')
            stats['queues'] = self._parse_queue_stats(output)
        except:
            pass
        
        return stats
    
    def _parse_port_stats(self, output):
        """Parse ovs-ofctl dump-ports output"""
        port_stats = {}
        
        # Example output line:
        # port  1: rx pkts=100, bytes=10000, drop=0, errs=0, frame=0, over=0, crc=0
        #          tx pkts=100, bytes=10000, drop=0, errs=0, coll=0
        
        for line in output.split('\n'):
            if 'port' in line and ':' in line:
                try:
                    parts = line.split(':')
                    port_num = parts[0].strip().split()[-1]
                    
                    # Extract RX stats
                    rx_match = re.search(r'rx pkts=(\d+).*?bytes=(\d+).*?drop=(\d+)', line)
                    tx_match = re.search(r'tx pkts=(\d+).*?bytes=(\d+).*?drop=(\d+)', line)
                    
                    if rx_match and tx_match:
                        port_stats[port_num] = {
                            'rx_packets': int(rx_match.group(1)),
                            'rx_bytes': int(rx_match.group(2)),
                            'rx_drops': int(rx_match.group(3)),
                            'tx_packets': int(tx_match.group(1)),
                            'tx_bytes': int(tx_match.group(2)),
                            'tx_drops': int(tx_match.group(3))
                        }
                except:
                    continue
        
        return port_stats
    
    def _parse_flow_stats(self, output):
        """Parse ovs-ofctl dump-flows output"""
        flow_stats = []
        
        for line in output.split('\n'):
            if 'n_packets' in line:
                try:
                    # Extract packet and byte counts
                    pkt_match = re.search(r'n_packets=(\d+)', line)
                    byte_match = re.search(r'n_bytes=(\d+)', line)
                    
                    if pkt_match and byte_match:
                        flow_stats.append({
                            'packets': int(pkt_match.group(1)),
                            'bytes': int(byte_match.group(1))
                        })
                except:
                    continue
        
        return flow_stats
    
    def _parse_queue_stats(self, output):
        """Parse ovs-ofctl queue-stats output"""
        queue_stats = {}
        
        # Parse queue statistics if available
        # Format varies by OVS version
        
        return queue_stats
    
    def compute_link_utilization(self):
        """Compute link utilization over time"""
        if len(self.samples) < 2:
            return {}
        
        utilization = {}
        
        for i in range(1, len(self.samples)):
            prev_sample = self.samples[i-1]
            curr_sample = self.samples[i]
            
            for switch_name in curr_sample['switches']:
                if switch_name not in prev_sample['switches']:
                    continue
                
                prev_ports = prev_sample['switches'][switch_name]['ports']
                curr_ports = curr_sample['switches'][switch_name]['ports']
                
                for port_num in curr_ports:
                    if port_num not in prev_ports:
                        continue
                    
                    # Calculate bytes transmitted in interval
                    bytes_delta = (curr_ports[port_num]['tx_bytes'] - 
                                 prev_ports[port_num]['tx_bytes'])
                    
                    # Calculate utilization (assuming 1Gbps links)
                    link_capacity_bps = 1000 * 1000 * 1000  # 1 Gbps
                    bits_delta = bytes_delta * 8
                    time_delta = self.sample_interval
                    
                    util_pct = (bits_delta / time_delta) / link_capacity_bps * 100
                    
                    link_id = f"{switch_name}:{port_num}"
                    if link_id not in utilization:
                        utilization[link_id] = []
                    utilization[link_id].append(util_pct)
        
        return utilization
    
    def compute_tail_latency(self, percentile=99):
        """Compute tail latency from collected samples"""
        # This would be computed from flow completion times
        # For now, return placeholder
        return {}
    
    def get_statistics(self):
        """Get comprehensive statistics summary"""
        stats = {
            'total_samples': len(self.samples),
            'duration': 0,
            'link_utilization': {},
            'packet_drops': {},
            'flow_counts': {}
        }
        
        if len(self.samples) >= 2:
            start_time = datetime.fromisoformat(self.samples[0]['timestamp'])
            end_time = datetime.fromisoformat(self.samples[-1]['timestamp'])
            stats['duration'] = (end_time - start_time).total_seconds()
        
        # Compute link utilization
        link_util = self.compute_link_utilization()
        
        for link_id, utils in link_util.items():
            stats['link_utilization'][link_id] = {
                'mean': sum(utils) / len(utils) if utils else 0,
                'max': max(utils) if utils else 0,
                'min': min(utils) if utils else 0,
                'samples': len(utils)
            }
        
        # Compute packet drops
        if self.samples:
            last_sample = self.samples[-1]
            for switch_name, switch_stats in last_sample['switches'].items():
                for port_num, port_stats in switch_stats['ports'].items():
                    total_drops = port_stats['rx_drops'] + port_stats['tx_drops']
                    if total_drops > 0:
                        link_id = f"{switch_name}:{port_num}"
                        stats['packet_drops'][link_id] = total_drops
        
        return stats
    
    def save_results(self, filename):
        """Save monitoring results to file"""
        data = {
            'samples': self.samples,
            'statistics': self.get_statistics()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"*** Monitoring results saved to {filename}")
    
    def print_summary(self):
        """Print summary of collected statistics"""
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("NETWORK MONITORING SUMMARY")
        print("="*60)
        print(f"Duration: {stats['duration']:.2f} seconds")
        print(f"Samples collected: {stats['total_samples']}")
        
        print("\nLink Utilization:")
        for link_id, util in stats['link_utilization'].items():
            print(f"  {link_id}: mean={util['mean']:.2f}%, "
                  f"max={util['max']:.2f}%, min={util['min']:.2f}%")
        
        if stats['packet_drops']:
            print("\nPacket Drops:")
            for link_id, drops in stats['packet_drops'].items():
                print(f"  {link_id}: {drops} packets")
        else:
            print("\nNo packet drops detected")
        
        print("="*60)


class FlowCompletionTracker:
    """Track flow completion times for FCT analysis"""
    
    def __init__(self):
        self.flows = {}
        self.completed_flows = []
    
    def start_flow(self, flow_id, src, dst, size):
        """Record flow start"""
        self.flows[flow_id] = {
            'src': src,
            'dst': dst,
            'size': size,
            'start_time': time.time()
        }
    
    def end_flow(self, flow_id):
        """Record flow completion"""
        if flow_id in self.flows:
            flow = self.flows[flow_id]
            flow['end_time'] = time.time()
            flow['fct'] = flow['end_time'] - flow['start_time']
            self.completed_flows.append(flow)
            del self.flows[flow_id]
    
    def get_fct_stats(self):
        """Get FCT statistics"""
        if not self.completed_flows:
            return {}
        
        fcts = [flow['fct'] for flow in self.completed_flows]
        fcts.sort()
        
        n = len(fcts)
        return {
            'count': n,
            'mean': sum(fcts) / n,
            'median': fcts[n // 2],
            'p95': fcts[int(n * 0.95)] if n > 0 else 0,
            'p99': fcts[int(n * 0.99)] if n > 0 else 0,
            'max': max(fcts),
            'min': min(fcts)
        }


if __name__ == '__main__':
    print("Network Monitoring Module")
    print("Use with Mininet network for performance measurement")
