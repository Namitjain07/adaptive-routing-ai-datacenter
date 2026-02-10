# Routing Strategy Design Document

## Project: Adaptive and Load-Aware Routing for AI Data Center Fabrics

**Date**: Week 3 Deliverable  
**Author**: NAI Project Team

---

## 1. Overview

This document outlines the routing strategy design for comparing static ECMP routing with adaptive, load-aware routing schemes in a leaf-spine data center fabric optimized for AI/ML training workloads.

### 1.1 Problem Statement

AI/ML distributed training generates highly synchronized, all-to-all traffic patterns that create:
- **Incast congestion**: Many senders to few receivers
- **Synchronized bursts**: Periodic gradient exchange
- **Load imbalance**: Static hashing can cause hotspots
- **Tail latency sensitivity**: Stragglers impact iteration time

### 1.2 Objectives

1. Implement baseline ECMP routing for comparison
2. Design adaptive routing schemes that react to congestion
3. Evaluate performance under realistic AI traffic patterns
4. Quantify improvements in throughput, latency, and load balance

---

## 2. Topology Design

### 2.1 Leaf-Spine Architecture

**Configuration:**
- 4 spine switches (scalable to 8)
- 4 leaf switches (scalable to 8)
- 4 hosts per leaf (16 total, up to 64)
- Full mesh: each leaf connects to all spines
- Link capacity: 1 Gbps
- Link delay: 1 ms

**Characteristics:**
- **Bisection bandwidth**: Full bisection (4 × 1Gbps = 4Gbps)
- **Path diversity**: 4 equal-cost paths between any leaf pair
- **Hop count**: Uniform 2-hop (host→leaf→spine→leaf→host)

### 2.2 Benefits for AI Workloads

- **High bandwidth**: Multiple paths for all-to-all traffic
- **Low latency**: 2-hop deterministic paths
- **Path diversity**: Enables load balancing
- **Scalability**: Easy to add spines/leaves

---

## 3. Routing Strategies

### 3.1 Baseline: ECMP Routing

**Mechanism:**
- Static 5-tuple hash: (src_ip, dst_ip, src_port, dst_port, protocol)
- Hash modulo number of paths → path selection
- OpenFlow select groups for implementation

**Advantages:**
- ✓ Simple and well-understood
- ✓ No state required
- ✓ Deterministic per-flow routing
- ✓ Hardware support widely available

**Disadvantages:**
- ✗ No congestion awareness
- ✗ Hash collisions cause imbalance
- ✗ Poor performance with synchronized traffic
- ✗ Cannot adapt to failures or congestion

**Implementation Details:**
```
For each destination subnet:
  1. Compute available paths (all spines)
  2. Create OpenFlow select group with buckets (one per spine)
  3. Install flow: match dst_ip → group:{group_id}
  4. OVS performs hash-based selection
```

### 3.2 Adaptive: Flowlet-Based Routing

**Mechanism:**
- Detect flowlet boundaries (idle gaps > threshold)
- Independently route each flowlet
- Use least-loaded path for new flowlets
- Maintain packet order within flowlets

**Key Parameters:**
- **Flowlet timeout**: 50ms (configurable)
- **Load metric**: Estimated queue length or utilization
- **Update frequency**: Per-flowlet (not per-packet)

**Advantages:**
- ✓ Maintains packet ordering within bursts
- ✓ Adapts to congestion without per-packet overhead
- ✓ Works well with bursty AI traffic
- ✓ No reordering issues

**Disadvantages:**
- ✗ Requires flowlet timeout tuning
- ✗ State overhead (flowlet table)
- ✗ Delay between load updates

**Algorithm:**
```python
def route_flowlet(flow_key, current_time):
    if flow_key in flowlet_table:
        last_time, last_path = flowlet_table[flow_key]
        if current_time - last_time < FLOWLET_TIMEOUT:
            # Same flowlet - use same path
            return last_path
    
    # New flowlet - select least loaded path
    selected_path = min(available_paths, key=lambda p: path_load[p])
    flowlet_table[flow_key] = (current_time, selected_path)
    return selected_path
```

### 3.3 Adaptive: Congestion-Aware Routing

**Mechanism:**
- Monitor link utilization in real-time
- Track queue lengths at switches
- Route new flows away from congested links
- Proactive congestion avoidance

**Key Parameters:**
- **Probe interval**: 100ms
- **Congestion threshold**: 70% utilization
- **Load metric**: Queue depth + utilization

**Advantages:**
- ✓ Real-time congestion awareness
- ✓ Proactive congestion avoidance
- ✓ Can react to transient congestion
- ✓ Better for elephant flows

**Disadvantages:**
- ✗ High monitoring overhead
- ✗ Potential packet reordering
- ✗ Delayed reaction to rapid changes

**Algorithm:**
```python
def route_congestion_aware(src, dst):
    path_scores = {}
    for path in available_paths:
        congestion_score = 0
        for link in path:
            utilization = get_link_utilization(link)
            queue_depth = get_queue_depth(link)
            congestion_score += utilization + (queue_depth / MAX_QUEUE)
        path_scores[path] = congestion_score
    
    # Select least congested path
    return min(path_scores, key=path_scores.get)
```

### 3.4 Hybrid Approach

Combine flowlet-based and congestion-aware:
- Use flowlet boundaries for rerouting opportunities
- Select paths based on congestion metrics
- Best of both: ordering + congestion awareness

---

## 4. Traffic Patterns

### 4.1 All-to-All Traffic

**Characteristics:**
- Every host sends to every other host
- Simulates gradient exchange in data-parallel training
- High-level of path multiplexing

**Parameters:**
- Flows: N × (N-1) for N hosts
- Per-flow bandwidth: 100 Mbps
- Duration: 10-60 seconds
- Protocol: TCP (for reliability)

### 4.2 AllReduce Pattern

**Characteristics:**
- Ring-based collective communication
- Two phases: Reduce-Scatter + AllGather
- (N-1) steps per phase
- Simulates Horovod/PyTorch DDP

**Algorithm:**
```
Phase 1: Reduce-Scatter
  For step in 0 to N-1:
    Each host sends chunk to next host in ring

Phase 2: AllGather
  For step in 0 to N-1:
    Each host sends chunk to next host in ring
```

### 4.3 Bursty Traffic

**Characteristics:**
- Periodic bursts with idle gaps
- Simulates compute + communicate pattern
- Burst size: 100 MB
- Idle time: 100 ms

---

## 5. Performance Metrics

### 5.1 Throughput

**Definition**: Aggregate goodput across all flows

**Measurement**:
- Per-flow throughput from iperf3
- Aggregate: sum of all flows
- Time-series: throughput over time

**Target**: Maximize aggregate throughput

### 5.2 Flow Completion Time (FCT)

**Definition**: Time from flow start to completion

**Measurement**:
- Record start and end timestamps
- Compute FCT per flow
- Analyze distribution: mean, median, P95, P99

**Target**: Minimize tail latency (P99)

### 5.3 Load Balance

**Definition**: Uniformity of link utilization

**Measurement**:
- Per-link utilization from OVS
- Compute standard deviation
- Balance score: 1 - (std / mean)

**Target**: Maximize balance score (closer to 1)

### 5.4 Packet Drops

**Definition**: Packets dropped due to congestion

**Measurement**:
- Query OVS port statistics
- Count TX/RX drops per port
- Aggregate across all ports

**Target**: Minimize drops

### 5.5 Congestion Duration

**Definition**: Time spent in congested state

**Measurement**:
- Monitor utilization > threshold
- Count time intervals above threshold

**Target**: Minimize congestion time

---

## 6. Experimental Design

### 6.1 Experiment Matrix

| Routing | Traffic | Duration | Runs |
|---------|---------|----------|------|
| ECMP | All-to-All | 30s | 3 |
| ECMP | AllReduce | 30s | 3 |
| ECMP | Bursty | 30s | 3 |
| Flowlet | All-to-All | 30s | 3 |
| Flowlet | AllReduce | 30s | 3 |
| Flowlet | Bursty | 30s | 3 |
| Congestion | All-to-All | 30s | 3 |
| Hybrid | All-to-All | 30s | 3 |

### 6.2 Controlled Variables

- Topology: 4×4 leaf-spine, 16 hosts
- Link capacity: 1 Gbps
- Link delay: 1 ms
- Per-flow bandwidth: 100 Mbps (for all-to-all)

### 6.3 Measured Variables

- Aggregate throughput
- Per-flow FCT (mean, P95, P99)
- Link utilization (mean, std, max)
- Packet drops
- Load balance score

---

## 7. Expected Results

### 7.1 ECMP Performance

**Strengths:**
- Predictable behavior
- Good performance with diverse flows

**Weaknesses:**
- Poor with synchronized traffic
- Hash collisions → imbalance
- High tail latency under congestion

**Expected Metrics:**
- Throughput: 60-70% of capacity
- P99 FCT: 2-3× mean FCT
- Load balance: 0.6-0.7
- Packet drops: High under congestion

### 7.2 Adaptive Performance

**Strengths:**
- Better load balance
- Lower tail latency
- Fewer packet drops

**Weaknesses:**
- Slightly higher complexity
- Monitoring overhead

**Expected Metrics:**
- Throughput: 75-85% of capacity (+10-15%)
- P99 FCT: 1.5-2× mean FCT (-30-50%)
- Load balance: 0.8-0.9 (+20-30%)
- Packet drops: 40-60% reduction

---

## 8. Implementation Plan

### Week 3: ✅ Design Complete
- Topology specification
- Routing algorithm design
- Traffic pattern definition
- Metrics specification

### Week 4-5: Implementation
- Mininet topology
- ECMP routing (OpenFlow)
- Adaptive routing
- Traffic generators
- Monitoring tools

### Week 6: Testing & Demo
- Run experiments
- Collect metrics
- Create visualization
- **Video demonstration**

### Week 7-8: Analysis
- Statistical analysis
- Comparison charts
- Identify optimal configurations

### Midterm: Demo
- Live ECMP vs Adaptive comparison
- Performance metrics presentation

### End-term: Final Report
- Comprehensive analysis
- Detailed comparison
- Conclusions and recommendations

---

## 9. Success Criteria

1. ✓ Functional leaf-spine topology in Mininet
2. ✓ Working ECMP and Adaptive routing implementations
3. ✓ Realistic AI traffic generation
4. ✓ Comprehensive metrics collection
5. ✓ Measurable performance improvements (>10% throughput, >20% tail latency)
6. ✓ Load balance improvement (>15%)
7. ✓ Packet drop reduction (>30%)

---

## 10. Future Extensions

- [ ] Hardware testbed validation
- [ ] Integration with SDN controller (ONOS)
- [ ] Support for priority scheduling
- [ ] Multi-tenant scenarios
- [ ] Failure recovery mechanisms
- [ ] Machine learning-based routing

---

## 11. References

1. Al-Fares et al., "A Scalable, Commodity Data Center Network Architecture", SIGCOMM 2008
2. Alizadeh et al., "CONGA: Distributed Congestion-Aware Load Balancing", SIGCOMM 2014
3. Kabbani et al., "FlowBender: Flow-level Adaptive Routing", CoNEXT 2014
4. Vanini et al., "Let It Flow: Resilient Asymmetric Load Balancing", NSDI 2017
5. Li et al., "HPCC: High Precision Congestion Control", SIGCOMM 2019

---

**Document Status**: Complete ✅  
**Review Date**: Week 3  
**Next Update**: Week 6 (Post-Implementation)
