#!/usr/bin/env python3
"""
Leaf-Spine Topology for AI Data Center Fabric Simulation
A two-tier Clos network with configurable number of leaf and spine switches.
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
import argparse
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import get_logger

logger = get_logger('topology')


class LeafSpineTopo(Topo):
    """
    Leaf-Spine Topology
    
    Parameters:
    - num_spines: Number of spine switches (default: 4)
    - num_leaves: Number of leaf switches (default: 4)
    - hosts_per_leaf: Number of hosts per leaf (default: 4)
    - host_leaf_bw: Host-Leaf link bandwidth in Mbps (default: 20)
    - leaf_spine_bw: Leaf-Spine link bandwidth in Mbps (default: 10)
    - delay: Link delay (default: '1ms')
    - queue_size: Queue size in packets (default: 200)
    """
    
    def __init__(self, num_spines=4, num_leaves=4, hosts_per_leaf=4, 
                 host_leaf_bw=20, leaf_spine_bw=10, delay='1ms', queue_size=200, **opts):
        Topo.__init__(self, **opts)
        
        self.num_spines = num_spines
        self.num_leaves = num_leaves
        self.hosts_per_leaf = hosts_per_leaf
        self.host_leaf_bw = host_leaf_bw
        self.leaf_spine_bw = leaf_spine_bw
        self.delay = delay
        self.queue_size = queue_size
        
        logger.info(f"Initializing Leaf-Spine topology: {num_spines} spines, {num_leaves} leaves, "
                   f"{hosts_per_leaf} hosts/leaf, Host-Leaf: {host_leaf_bw} Mbps, "
                   f"Leaf-Spine: {leaf_spine_bw} Mbps, Queue: {queue_size} packets")
        
        # Create spine switches
        spines = []
        for s in range(num_spines):
            spine = self.addSwitch(f'spine{s+1}', dpid=f'{s+1:016x}')
            spines.append(spine)
            info(f'*** Adding spine switch: {spine}\n')
        
        # Create leaf switches and hosts
        leaves = []
        host_id = 1
        for l in range(num_leaves):
            leaf = self.addSwitch(f'leaf{l+1}', dpid=f'{l+1+num_spines:016x}')
            leaves.append(leaf)
            info(f'*** Adding leaf switch: {leaf}\n')
            
            # Connect hosts to this leaf
            for h in range(hosts_per_leaf):
                host = self.addHost(f'h{host_id}', 
                                   ip=f'10.0.{l+1}.{h+1}/24',
                                   mac=f'00:00:00:00:{l+1:02x}:{h+1:02x}')
                self.addLink(host, leaf, bw=host_leaf_bw, delay=delay, max_queue_size=queue_size)
                info(f'*** Adding host: {host} -> {leaf}\n')
                host_id += 1
            
            # Connect this leaf to all spines (full mesh)
            for spine in spines:
                self.addLink(leaf, spine, bw=leaf_spine_bw, delay=delay, max_queue_size=queue_size)
                info(f'*** Adding link: {leaf} <-> {spine}\n')
        
        logger.info(f"Topology created: {len(spines)} spines, {len(leaves)} leaves, "
                   f"{host_id-1} total hosts")


def create_network(num_spines=4, num_leaves=4, hosts_per_leaf=4):
    """Create and configure the Mininet network"""
    
    logger.info(f"Creating Mininet network with Leaf-Spine topology")
    
    topo = LeafSpineTopo(num_spines=num_spines, 
                        num_leaves=num_leaves, 
                        hosts_per_leaf=hosts_per_leaf,
                        host_leaf_bw=20,  # Host-Leaf: 20 Mbps
                        leaf_spine_bw=10,  # Leaf-Spine: 10 Mbps
                        delay='1ms',
                        queue_size=200)  # Queue: 200 packets
    
    net = Mininet(topo=topo,
                  switch=OVSKernelSwitch,
                  link=TCLink,
                  controller=None,  # We use static routing, no controller needed
                  autoSetMacs=True,
                  autoStaticArp=True,
                  waitConnected=False)  # Disable waiting for controller
    
    logger.info("Mininet network created successfully")
    return net


def run_topology(num_spines=4, num_leaves=4, hosts_per_leaf=4):
    """Run the leaf-spine topology"""
    
    setLogLevel('info')
    logger.info('Starting Leaf-Spine Topology')
    
    info('*** Creating Leaf-Spine Topology\n')
    info(f'*** Spines: {num_spines}, Leaves: {num_leaves}, Hosts/Leaf: {hosts_per_leaf}\n')
    
    net = create_network(num_spines, num_leaves, hosts_per_leaf)
    
    info('*** Starting network\n')
    net.start()
    
    info('*** Network topology:\n')
    info(f'*** Total hosts: {num_leaves * hosts_per_leaf}\n')
    info(f'*** Total switches: {num_spines + num_leaves}\n')
    info(f'*** Spine-Leaf links: {num_spines * num_leaves}\n')
    
    info('*** Running CLI\n')
    CLI(net)
    
    logger.info('Stopping network')
    info('*** Stopping network\n')
    net.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Leaf-Spine Topology for Mininet')
    parser.add_argument('--spines', type=int, default=4, 
                       help='Number of spine switches (default: 4)')
    parser.add_argument('--leaves', type=int, default=4,
                       help='Number of leaf switches (default: 4)')
    parser.add_argument('--hosts', type=int, default=4,
                       help='Number of hosts per leaf (default: 4)')
    
    args = parser.parse_args()
    
    from utils.logger import setup_logger
    setup_logger('topology', level=logging.INFO)
    
    run_topology(num_spines=args.spines, 
                num_leaves=args.leaves, 
                hosts_per_leaf=args.hosts)
