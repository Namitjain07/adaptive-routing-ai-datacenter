#!/bin/bash

# Installation script for AI Data Center Routing Simulation

echo "=============================================="
echo "AI Data Center Routing Simulation - Setup"
echo "=============================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo ""
echo "Step 1: Updating package lists..."
apt-get update

echo ""
echo "Step 2: Installing Mininet..."
apt-get install -y mininet

echo ""
echo "Step 3: Installing Open vSwitch..."
apt-get install -y openvswitch-switch

echo ""
echo "Step 4: Installing iperf3..."
apt-get install -y iperf3

echo ""
echo "Step 5: Installing Python dependencies..."
apt-get install -y python3-pip python3-matplotlib python3-numpy

echo ""
echo "Step 6: Installing Python packages..."
pip3 install -r requirements.txt

echo ""
echo "Step 7: Testing Mininet installation..."
mn --test pingall

echo ""
echo "Step 8: Cleaning up Mininet..."
mn -c

echo ""
echo "=============================================="
echo "Installation complete!"
echo "=============================================="
echo ""
echo "Quick start:"
echo "  sudo python3 run_experiment.py --mode comparison --duration 30"
echo ""
echo "For help:"
echo "  python3 run_experiment.py --help"
echo ""
