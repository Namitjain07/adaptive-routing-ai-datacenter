#!/bin/bash
# Quick demonstration of hash collision scenarios
# Runs short tests to show ECMP vs Adaptive difference

echo "========================================================================"
echo "HASH COLLISION DEMONSTRATION"
echo "Quick test showing ECMP collision problem and Adaptive solution"
echo "========================================================================"
echo ""
echo "This demo will:"
echo "  1. Create elephant flows that collide under ECMP"
echo "  2. Run with ECMP routing (expect imbalance)"
echo "  3. Run with Adaptive routing (expect balance)"
echo "  4. Compare results"
echo ""
echo "Duration: ~3 minutes total"
echo ""
read -p "Press Enter to start..."

# Create output directory
mkdir -p collision_demo

echo ""
echo "========================================================================"
echo "STEP 1: Testing ECMP with Elephant Flow Collisions"
echo "========================================================================"
echo ""

# Run ECMP test (short duration for demo)
sudo python3 test_collision_scenarios.py \
    --test elephant \
    --routing ecmp \
    --duration 10 \
    --spines 4 \
    --leaves 4 \
    --hosts 4 \
    --output collision_demo

echo ""
echo "Waiting 5 seconds before next test..."
sleep 5

echo ""
echo "========================================================================"
echo "STEP 2: Testing Adaptive Routing with Same Traffic"
echo "========================================================================"
echo ""

# Run Adaptive test
sudo python3 test_collision_scenarios.py \
    --test elephant \
    --routing adaptive \
    --duration 10 \
    --spines 4 \
    --leaves 4 \
    --hosts 4 \
    --output collision_demo

echo ""
echo "========================================================================"
echo "DEMONSTRATION COMPLETE"
echo "========================================================================"
echo ""
echo "Key Observations:"
echo "  - ECMP: Check for 'SEVERE IMBALANCE' or 'MODERATE IMBALANCE' messages"
echo "  - Adaptive: Should show 'GOOD BALANCE' with lower imbalance factor"
echo ""
echo "Results saved to: collision_demo/"
echo ""
echo "To run full test suite with all scenarios:"
echo "  sudo python3 test_collision_scenarios.py --routing comparison --test all"
echo ""
