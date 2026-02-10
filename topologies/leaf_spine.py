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


class LeafSpineTopo(Topo):
    """
    Leaf-Spine Topology
    
    Parameters:
    - num_spines: Number of spine switches (default: 4)
    - num_leaves: Number of leaf switches (default: 4)
    - hosts_per_leaf: Number of hosts per leaf (default: 4)
    - bw: Link bandwidth in Mbps (default: 1000)
    - delay: Link delay (default: '1ms')
    """
    
    def __init__(self, num_spines=4, num_leaves=4, hosts_per_leaf=4, 
                 bw=1000, delay='1ms', **opts):
        Topo.__init__(self, **opts)
        
        self.num_spines = num_spines
        self.num_leaves = num_leaves
        self.hosts_per_leaf = hosts_per_leaf
        self.bw = bw
        self.delay = delay
        
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
                self.addLink(host, leaf, bw=bw, delay=delay, max_queue_size=1000)
                info(f'*** Adding host: {host} -> {leaf}\n')
                host_id += 1
            
            # Connect this leaf to all spines (full mesh)
            for spine in spines:
                self.addLink(leaf, spine, bw=bw, delay=delay, max_queue_size=1000)
                info(f'*** Adding link: {leaf} <-> {spine}\n')


def create_network(num_spines=4, num_leaves=4, hosts_per_leaf=4):
    """Create and configure the Mininet network"""
    
    topo = LeafSpineTopo(num_spines=num_spines, 
                        num_leaves=num_leaves, 
                        hosts_per_leaf=hosts_per_leaf,
                        bw=10,  # 10 Mbps per link (lower bandwidth avoids HTB quantum warnings)
                        delay='1ms')
    
    net = Mininet(topo=topo,
                  switch=OVSKernelSwitch,
                  link=TCLink,
                  controller=None,  # We use static routing, no controller needed
                  autoSetMacs=True,
                  autoStaticArp=True,
                  waitConnected=False)  # Disable waiting for controller
    
    return net


def run_topology(num_spines=4, num_leaves=4, hosts_per_leaf=4):
    """Run the leaf-spine topology"""
    
    setLogLevel('info')
    
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
    
    run_topology(num_spines=args.spines, 
                num_leaves=args.leaves, 
                hosts_per_leaf=args.hosts)
