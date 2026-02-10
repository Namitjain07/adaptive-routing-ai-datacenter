#!/usr/bin/env python3
"""
ECMP (Equal-Cost Multi-Path) Routing Implementation
Static hash-based multipath routing using OVS flow rules.
"""

import json
import time
from collections import defaultdict


class ECMPRouter:
    """
    ECMP routing implementation using OpenFlow rules.
    Uses hash-based load balancing across equal-cost paths.
    """
    
    def __init__(self, controller):
        self.controller = controller
        self.topology = {}
        self.flow_tables = defaultdict(list)
        
    def compute_ecmp_paths(self, src, dst, topology):
        """
        Compute all equal-cost paths between src and dst.
        For leaf-spine, this is straightforward: all paths through spines are equal.
        
        Args:
            src: Source switch
            dst: Destination switch
            topology: Network topology graph
            
        Returns:
            List of equal-cost paths
        """
        paths = []
        
        # In leaf-spine: if same leaf, direct path
        if src == dst:
            return [[src]]
        
        # If both are leaves, path goes through any spine
        if 'leaf' in src and 'leaf' in dst:
            spines = [node for node in topology if 'spine' in node]
            for spine in spines:
                paths.append([src, spine, dst])
        
        return paths
    
    def install_ecmp_rules(self, net, routing_table):
        """
        Install ECMP flow rules on all switches.
        
        Args:
            net: Mininet network object
            routing_table: Pre-computed routing table with ECMP groups
        """
        print("*** Installing ECMP flow rules...")
        
        for switch_name, rules in routing_table.items():
            switch = net.get(switch_name)
            if switch is None:
                continue
            
            # Clear existing flows
            switch.cmd(f'ovs-ofctl del-flows {switch_name}')
            
            # Install new ECMP rules
            for rule in rules:
                dst_ip = rule['dst_ip']
                out_ports = rule['out_ports']
                
                if len(out_ports) == 1:
                    # Single path - simple forwarding
                    flow = (f'priority=100,ip,nw_dst={dst_ip},'
                           f'actions=output:{out_ports[0]}')
                    switch.cmd(f'ovs-ofctl add-flow {switch_name} "{flow}"')
                else:
                    # Multiple paths - use group table for ECMP
                    group_id = hash(f"{switch_name}{dst_ip}") % 10000
                    
                    # Create select group with multiple buckets
                    buckets = ','.join([f'bucket=output:{port}' 
                                       for port in out_ports])
                    group_cmd = (f'ovs-ofctl add-group {switch_name} '
                               f'group_id={group_id},type=select,{buckets}')
                    switch.cmd(group_cmd)
                    
                    # Add flow pointing to group
                    flow = (f'priority=100,ip,nw_dst={dst_ip},'
                           f'actions=group:{group_id}')
                    switch.cmd(f'ovs-ofctl add-flow {switch_name} "{flow}"')
            
            # Default flow - flood
            switch.cmd(f'ovs-ofctl add-flow {switch_name} "priority=0,actions=flood"')
        
        print("*** ECMP rules installed successfully")
    
    def build_routing_table(self, net, topology_info):
        """
        Build ECMP routing table for leaf-spine topology.
        
        Args:
            net: Mininet network object
            topology_info: Dict with spine/leaf/host information
            
        Returns:
            routing_table: Dict mapping switches to forwarding rules
        """
        routing_table = defaultdict(list)
        
        num_spines = topology_info['num_spines']
        num_leaves = topology_info['num_leaves']
        hosts_per_leaf = topology_info['hosts_per_leaf']
        
        # Get all switches
        spines = [f'spine{i+1}' for i in range(num_spines)]
        leaves = [f'leaf{i+1}' for i in range(num_leaves)]
        
        # Build routing rules for each leaf switch
        for leaf_idx, leaf in enumerate(leaves):
            leaf_num = leaf_idx + 1
            switch = net.get(leaf)
            
            # Get port mappings for this leaf
            port_to_spine = {}
            for intf in switch.intfList():
                intf_name = intf.name
                link = intf.link
                if link:
                    peer = link.intf1 if link.intf2 == intf else link.intf2
                    if 'spine' in peer.node.name:
                        port_num = int(intf_name.replace(f'{leaf}-eth', ''))
                        port_to_spine[peer.node.name] = port_num
            
            # Rules for local hosts (direct forwarding)
            for h in range(hosts_per_leaf):
                host_ip = f'10.0.{leaf_num}.{h+1}'
                host_port = h + 1  # Assuming first N ports are for hosts
                
                routing_table[leaf].append({
                    'dst_ip': host_ip,
                    'out_ports': [host_port]
                })
            
            # Rules for remote hosts (ECMP across all spines)
            for remote_leaf_idx, remote_leaf in enumerate(leaves):
                if remote_leaf_idx == leaf_idx:
                    continue
                
                remote_leaf_num = remote_leaf_idx + 1
                for h in range(hosts_per_leaf):
                    remote_ip = f'10.0.{remote_leaf_num}.{h+1}'
                    
                    # ECMP: use all available spine ports
                    spine_ports = list(port_to_spine.values())
                    
                    routing_table[leaf].append({
                        'dst_ip': remote_ip,
                        'out_ports': spine_ports
                    })
        
        # Build routing rules for each spine switch
        for spine in spines:
            switch = net.get(spine)
            
            # Get port mappings to leaves
            port_to_leaf = {}
            for intf in switch.intfList():
                intf_name = intf.name
                link = intf.link
                if link:
                    peer = link.intf1 if link.intf2 == intf else link.intf2
                    if 'leaf' in peer.node.name:
                        port_num = int(intf_name.replace(f'{spine}-eth', ''))
                        leaf_match = peer.node.name.replace('leaf', '')
                        port_to_leaf[int(leaf_match)] = port_num
            
            # Rules to forward to appropriate leaf based on destination IP
            for leaf_idx in range(num_leaves):
                leaf_num = leaf_idx + 1
                if leaf_num in port_to_leaf:
                    for h in range(hosts_per_leaf):
                        host_ip = f'10.0.{leaf_num}.{h+1}'
                        
                        routing_table[spine].append({
                            'dst_ip': host_ip,
                            'out_ports': [port_to_leaf[leaf_num]]
                        })
        
        return routing_table


def setup_ecmp_routing(net, num_spines=4, num_leaves=4, hosts_per_leaf=4):
    """
    Setup ECMP routing for the network.
    
    Args:
        net: Mininet network object
        num_spines: Number of spine switches
        num_leaves: Number of leaf switches
        hosts_per_leaf: Hosts per leaf switch
    """
    router = ECMPRouter(controller=None)
    
    topology_info = {
        'num_spines': num_spines,
        'num_leaves': num_leaves,
        'hosts_per_leaf': hosts_per_leaf
    }
    
    print("*** Building ECMP routing table...")
    routing_table = router.build_routing_table(net, topology_info)
    
    print("*** Installing ECMP rules...")
    router.install_ecmp_rules(net, routing_table)
    
    return router, routing_table


if __name__ == '__main__':
    print("ECMP Routing Module")
    print("Use this module with the leaf-spine topology")
