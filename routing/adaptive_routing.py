#!/usr/bin/env python3
"""
Adaptive Routing Implementation
Flowlet-based and congestion-aware routing for AI data center fabrics.
"""

import time
import threading
from collections import defaultdict, deque
import random


class FlowletRouter:
    """
    Flowlet-based adaptive routing.
    
    Flowlets are bursts of packets separated by idle periods.
    Each flowlet can take a different path, allowing load balancing
    while maintaining packet ordering within flowlets.
    """
    
    def __init__(self, flowlet_timeout=0.05):
        """
        Args:
            flowlet_timeout: Time gap (seconds) to consider new flowlet (default: 50ms)
        """
        self.flowlet_timeout = flowlet_timeout
        self.flowlet_table = {}  # (src, dst, flow_id) -> (last_time, path_id)
        self.path_loads = defaultdict(lambda: 0)  # path_id -> current load estimate
        self.lock = threading.Lock()
        
    def get_flowlet_path(self, flow_key, available_paths, current_time):
        """
        Determine which path to use for this flowlet.
        
        Args:
            flow_key: (src_ip, dst_ip, flow_id) tuple
            available_paths: List of available path IDs
            current_time: Current timestamp
            
        Returns:
            Selected path ID
        """
        with self.lock:
            if flow_key in self.flowlet_table:
                last_time, last_path = self.flowlet_table[flow_key]
                
                # If within flowlet timeout, use same path
                if current_time - last_time < self.flowlet_timeout:
                    self.flowlet_table[flow_key] = (current_time, last_path)
                    return last_path
            
            # New flowlet - select least loaded path
            selected_path = min(available_paths, 
                              key=lambda p: self.path_loads.get(p, 0))
            
            self.flowlet_table[flow_key] = (current_time, selected_path)
            return selected_path
    
    def update_path_load(self, path_id, load_delta):
        """Update the estimated load on a path"""
        with self.lock:
            self.path_loads[path_id] += load_delta


class CongestionAwareRouter:
    """
    Congestion-aware adaptive routing.
    
    Monitors link utilization and queue lengths to make routing decisions.
    Routes traffic away from congested paths.
    """
    
    def __init__(self, probe_interval=0.1, congestion_threshold=0.7):
        """
        Args:
            probe_interval: How often to probe link stats (seconds)
            congestion_threshold: Link utilization threshold for congestion (0-1)
        """
        self.probe_interval = probe_interval
        self.congestion_threshold = congestion_threshold
        self.link_stats = {}  # (switch, port) -> {'util': float, 'queue': int}
        self.path_congestion = defaultdict(lambda: 0.0)
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self, net):
        """Start background monitoring of network statistics"""
        self.monitoring = True
        self.net = net
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self):
        """Background loop to collect link statistics"""
        while self.monitoring:
            self._collect_stats()
            time.sleep(self.probe_interval)
    
    def _collect_stats(self):
        """Collect statistics from all switches"""
        if not hasattr(self, 'net'):
            return
        
        for switch in self.net.switches:
            switch_name = switch.name
            
            # Get port statistics using ovs-ofctl
            result = switch.cmd(f'ovs-ofctl dump-ports {switch_name}')
            
            # Parse port stats (simplified)
            # In real implementation, parse TX/RX bytes and compute utilization
            for intf in switch.intfList():
                if intf.name == 'lo':
                    continue
                
                port_num = int(intf.name.replace(f'{switch_name}-eth', ''))
                
                # Simulate utilization (in real version, compute from byte counts)
                # For simulation, we'll populate this during traffic generation
                self.link_stats[(switch_name, port_num)] = {
                    'util': 0.0,
                    'queue': 0,
                    'bytes_tx': 0,
                    'bytes_rx': 0
                }
    
    def get_path_score(self, path_id, path_links):
        """
        Compute congestion score for a path.
        Lower score = less congested = preferred.
        
        Args:
            path_id: Path identifier
            path_links: List of (switch, port) tuples in the path
            
        Returns:
            Congestion score (0-1, lower is better)
        """
        if not path_links:
            return 0.0
        
        total_congestion = 0.0
        for switch, port in path_links:
            stats = self.link_stats.get((switch, port), {'util': 0.0})
            total_congestion += stats['util']
        
        avg_congestion = total_congestion / len(path_links)
        return avg_congestion
    
    def select_path(self, available_paths, path_links_map):
        """
        Select best path based on congestion.
        
        Args:
            available_paths: List of available path IDs
            path_links_map: Dict mapping path_id -> list of (switch, port)
            
        Returns:
            Selected path ID
        """
        path_scores = {}
        for path_id in available_paths:
            path_links = path_links_map.get(path_id, [])
            path_scores[path_id] = self.get_path_score(path_id, path_links)
        
        # Select path with lowest congestion
        best_path = min(path_scores.keys(), key=lambda p: path_scores[p])
        return best_path


class AdaptiveRoutingController:
    """
    Combined adaptive routing controller.
    Integrates flowlet-based and congestion-aware routing.
    """
    
    def __init__(self, mode='flowlet', flowlet_timeout=0.05, 
                 congestion_threshold=0.7):
        """
        Args:
            mode: 'flowlet', 'congestion', or 'hybrid'
            flowlet_timeout: Flowlet timeout in seconds
            congestion_threshold: Congestion detection threshold
        """
        self.mode = mode
        self.flowlet_router = FlowletRouter(flowlet_timeout)
        self.congestion_router = CongestionAwareRouter(
            probe_interval=0.1,
            congestion_threshold=congestion_threshold
        )
        
    def start(self, net):
        """Start the adaptive routing controller"""
        if self.mode in ['congestion', 'hybrid']:
            self.congestion_router.start_monitoring(net)
        print(f"*** Adaptive routing started (mode: {self.mode})")
    
    def stop(self):
        """Stop the adaptive routing controller"""
        self.congestion_router.stop_monitoring()
        print("*** Adaptive routing stopped")
    
    def install_adaptive_rules(self, net, topology_info):
        """
        Install adaptive routing rules.
        
        For adaptive routing, we use more dynamic flow rules that can be
        updated based on network conditions.
        """
        print("*** Installing adaptive routing rules...")
        
        num_spines = topology_info['num_spines']
        num_leaves = topology_info['num_leaves']
        hosts_per_leaf = topology_info['hosts_per_leaf']
        
        leaves = [f'leaf{i+1}' for i in range(num_leaves)]
        spines = [f'spine{i+1}' for i in range(num_spines)]
        
        # Install rules on leaf switches
        for leaf_idx, leaf in enumerate(leaves):
            leaf_num = leaf_idx + 1
            switch = net.get(leaf)
            
            # Clear existing flows
            switch.cmd(f'ovs-ofctl del-flows {leaf}')
            
            # Get spine ports
            spine_ports = []
            for intf in switch.intfList():
                link = intf.link
                if link:
                    peer = link.intf1 if link.intf2 == intf else link.intf2
                    if 'spine' in peer.node.name:
                        port_num = int(intf.name.replace(f'{leaf}-eth', ''))
                        spine_ports.append(port_num)
            
            # For adaptive routing, we can use OpenFlow meters and groups
            # with selection algorithms that consider current load
            
            # Local hosts - direct forwarding
            for h in range(hosts_per_leaf):
                host_ip = f'10.0.{leaf_num}.{h+1}'
                host_port = h + 1
                flow = f'priority=100,ip,nw_dst={host_ip},actions=output:{host_port}'
                switch.cmd(f'ovs-ofctl add-flow {leaf} "{flow}"')
            
            # Remote hosts - adaptive multipath
            for remote_leaf_idx in range(num_leaves):
                if remote_leaf_idx == leaf_idx:
                    continue
                
                remote_leaf_num = remote_leaf_idx + 1
                for h in range(hosts_per_leaf):
                    remote_ip = f'10.0.{remote_leaf_num}.{h+1}'
                    
                    # Create select group with all spine ports
                    group_id = hash(f"{leaf}{remote_ip}") % 10000
                    buckets = ','.join([f'bucket=output:{port}' 
                                       for port in spine_ports])
                    
                    # Use select group type for load balancing
                    group_cmd = (f'ovs-ofctl add-group {leaf} '
                               f'group_id={group_id},type=select,{buckets}')
                    switch.cmd(group_cmd)
                    
                    # Add flow to group
                    flow = f'priority=100,ip,nw_dst={remote_ip},actions=group:{group_id}'
                    switch.cmd(f'ovs-ofctl add-flow {leaf} "{flow}"')
            
            # Default flow
            switch.cmd(f'ovs-ofctl add-flow {leaf} "priority=0,actions=flood"')
        
        # Install rules on spine switches (same as ECMP)
        for spine in spines:
            switch = net.get(spine)
            switch.cmd(f'ovs-ofctl del-flows {spine}')
            
            # Get port to leaf mappings
            port_to_leaf = {}
            for intf in switch.intfList():
                link = intf.link
                if link:
                    peer = link.intf1 if link.intf2 == intf else link.intf2
                    if 'leaf' in peer.node.name:
                        port_num = int(intf.name.replace(f'{spine}-eth', ''))
                        leaf_num = int(peer.node.name.replace('leaf', ''))
                        port_to_leaf[leaf_num] = port_num
            
            # Forward to appropriate leaf
            for leaf_num in port_to_leaf:
                for h in range(hosts_per_leaf):
                    host_ip = f'10.0.{leaf_num}.{h+1}'
                    flow = f'priority=100,ip,nw_dst={host_ip},actions=output:{port_to_leaf[leaf_num]}'
                    switch.cmd(f'ovs-ofctl add-flow {spine} "{flow}"')
            
            # Default flow
            switch.cmd(f'ovs-ofctl add-flow {spine} "priority=0,actions=flood"')
        
        print("*** Adaptive routing rules installed")


def setup_adaptive_routing(net, num_spines=4, num_leaves=4, hosts_per_leaf=4,
                          mode='flowlet'):
    """
    Setup adaptive routing for the network.
    
    Args:
        net: Mininet network object
        num_spines: Number of spine switches
        num_leaves: Number of leaf switches
        hosts_per_leaf: Hosts per leaf switch
        mode: 'flowlet', 'congestion', or 'hybrid'
    """
    controller = AdaptiveRoutingController(mode=mode)
    
    topology_info = {
        'num_spines': num_spines,
        'num_leaves': num_leaves,
        'hosts_per_leaf': hosts_per_leaf
    }
    
    controller.install_adaptive_rules(net, topology_info)
    controller.start(net)
    
    return controller


if __name__ == '__main__':
    print("Adaptive Routing Module")
    print("Supports flowlet-based and congestion-aware routing")
