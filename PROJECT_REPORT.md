# Adaptive and Load-Aware Routing for AI Data Center Fabrics
## Simulation Study

---

<div style="text-align: center; margin-top: 100px;">

### **Project Number:** P6

### **Project Title:**  
**Survey Adaptive and Load-Aware Routing for AI Data Center Fabrics**

<br>

### **Group Members:**
- **[Member 1 Name]** - [email1@university.edu]
- **[Member 2 Name]** - [email2@university.edu]  
- **[Member 3 Name]** - [email3@university.edu]
- **[Member 4 Name]** - [email4@university.edu]

<br>

### **Course:**  
AI for Networking and Networking for AI

<br>

### **Date:**  
February 11, 2026

</div>

---

<div style="page-break-after: always;"></div>

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Technology Background](#2-technology-background)
   - 2.1 [Core Concepts and Definitions](#21-core-concepts-and-definitions)
   - 2.2 [Use Cases and Key Performance Indicators](#22-use-cases-and-key-performance-indicators)
   - 2.3 [Literature Survey](#23-literature-survey)
   - 2.4 [Current Challenges and Limitations](#24-current-challenges-and-limitations)
3. [Problem Framing](#3-problem-framing)
   - 3.1 [Specific Problem Statement](#31-specific-problem-statement)
   - 3.2 [Scope and Assumptions](#32-scope-and-assumptions)
   - 3.3 [Timeliness and Importance](#33-timeliness-and-importance)
   - 3.4 [Expected Key Performance Indicators](#34-expected-key-performance-indicators)

---

<div style="page-break-after: always;"></div>

## 1. Executive Summary

### 1.1 Problem Overview

The exponential growth of artificial intelligence and machine learning workloads has fundamentally transformed data center network requirements. Modern distributed AI training—particularly for large language models (LLMs), computer vision models, and recommendation systems—generates highly synchronized, all-to-all communication patterns that differ dramatically from traditional web-scale traffic. These AI workloads exhibit periodic gradient exchange bursts during synchronized parameter updates, creating severe incast congestion events where many training nodes simultaneously communicate with few parameter servers or peer nodes.

Traditional data center routing protocols, particularly Equal-Cost Multi-Path (ECMP) routing, employ static hash-based load balancing that distributes flows across available paths using deterministic hashing of flow 5-tuples (source IP, destination IP, source port, destination port, protocol). While ECMP performs adequately for heterogeneous web traffic with random arrival patterns, it suffers critical performance degradation under AI training workloads due to:

1. **Hash collision-induced load imbalance**: Static hashing can cause multiple elephant flows to collide on the same path, creating hotspots while other paths remain underutilized.
2. **Congestion blindness**: ECMP lacks real-time network state awareness, routing packets into congested paths even when alternative uncongested paths exist.
3. **Tail latency amplification**: In synchronized training, the slowest worker determines iteration completion time; ECMP's inability to avoid congested paths leads to significant tail latency and reduced training efficiency.
4. **Incast susceptibility**: All-to-all communication patterns create many-to-one scenarios where ECMP cannot effectively distribute load.

### 1.2 Why This Matters for AI & Networking

The convergence of AI and networking presents both unprecedented challenges and opportunities. Network performance has emerged as a critical bottleneck in distributed AI training, with studies showing that communication can consume 40-90% of training time for large-scale models. As model sizes continue to grow exponentially (GPT-3: 175B parameters, GPT-4: estimated 1.7T parameters), the network must efficiently support:

- **High-bandwidth all-reduce operations**: Gradient synchronization requires all nodes to exchange data with all other nodes, generating $O(n^2)$ traffic patterns.
- **Synchronized bursts**: Training iterations create periodic traffic bursts every 100ms-1s, overwhelming static routing schemes.
- **Low tail latency**: As training is synchronous, stragglers directly impact iteration time and GPU utilization; 99th percentile latency often matters more than average latency.
- **Load balance**: Uneven link utilization leads to congestion on some paths while others remain idle, wasting expensive network capacity.

This project addresses a critical gap in network infrastructure for AI by exploring adaptive routing strategies that can dynamically respond to real-time congestion, improving resource utilization and training efficiency. Given that leading AI companies spend millions of dollars on GPU clusters, even modest improvements in network efficiency translate to substantial cost savings and faster time-to-solution for AI research and deployment.

### 1.3 Expected Contributions

This simulation study makes the following key contributions:

1. **Comparative Performance Analysis**: Quantitative evaluation of ECMP versus adaptive routing schemes under realistic AI training traffic, measuring tail flow completion time (FCT), link utilization balance, congestion duration, and throughput improvements.

2. **Flowlet-Based Adaptive Routing**: Implementation and evaluation of flowlet-aware routing that leverages temporal gaps in bursty traffic to dynamically rebalance load while maintaining packet ordering guarantees.

3. **Congestion-Aware Path Selection**: Development of a lightweight monitoring framework that tracks link utilization in real-time and steers new flowlets toward least-congested paths.

4. **Simulation Framework**: Creation of an extensible, reproducible Mininet-based simulation environment for leaf-spine topologies that can be used for further research in AI data center networking.

5. **Performance Metrics and Insights**: Comprehensive analysis of routing strategies using industry-standard KPIs, providing actionable insights for data center network operators deploying AI infrastructure.

The expected outcome is demonstrating 20-40% improvement in tail FCT and 15-30% better load balance compared to baseline ECMP, validating that adaptive routing can significantly enhance AI training efficiency on existing data center hardware.

---

<div style="page-break-after: always;"></div>

## 2. Technology Background

### 2.1 Core Concepts and Definitions

#### 2.1.1 Data Center Network Topologies

Modern data center networks employ specialized topologies optimized for high bisection bandwidth and scalable design:

**Leaf-Spine Architecture**: A two-tier Clos network topology where:
- **Leaf switches** (Top-of-Rack switches): Connect directly to servers/hosts and provide network access.
- **Spine switches** (aggregation layer): Form a non-blocking backplane connecting all leaf switches.
- **Full mesh connectivity**: Every leaf connects to every spine, providing $k$ equal-cost paths between any two leaves (where $k$ is the number of spines).
- **Properties**: Fixed 2-hop latency between any host pair, high path diversity, predictable performance.

**Advantages for AI Workloads**:
- **High bisection bandwidth**: All-to-all traffic benefits from full mesh interconnect.
- **Path diversity**: Multiple equal-cost paths enable load balancing.
- **Horizontal scalability**: Adding spines increases bandwidth proportionally.
- **Fault tolerance**: Network remains functional even if individual spines fail.

#### 2.1.2 Routing Strategies

**Equal-Cost Multi-Path (ECMP) Routing**:
- Distributes traffic across multiple equal-cost paths to the same destination.
- Uses hash function $h(\text{5-tuple}) \mod k$ where $k$ is the number of available paths.
- Implemented in hardware using Ternary Content-Addressable Memory (TCAM) for wire-speed forwarding.
- **Pros**: Stateless, simple, hardware-supported, deterministic per-flow routing.
- **Cons**: Static, congestion-oblivious, hash collisions cause imbalance, poor performance under correlated arrivals.

**Flowlet-Based Routing**:
- **Flowlet**: A burst of packets from the same flow separated by idle gaps (typically >50-100ms).
- Exploits natural temporal structure in bursty traffic to enable dynamic load balancing.
- Routes flowlets independently while maintaining packet order within each flowlet.
- **Key insight**: Idle gaps are large enough to drain queues, so different flowlets can take different paths without packet reordering.

**Congestion-Aware Routing**:
- Makes forwarding decisions based on real-time network state (queue lengths, link utilization, packet drops).
- **Metrics used**: Queue occupancy, Explicit Congestion Notification (ECN) marks, link utilization percentage.
- **Challenges**: Measurement overhead, timely state propagation, stability and oscillation avoidance.

**Adaptive Routing**:
- Combines flowlet detection with congestion awareness.
- Each new flowlet selects the least-loaded available path.
- Updates routing decisions as network conditions change.

#### 2.1.3 AI Training Communication Patterns

**Data Parallelism**:
- Model replicated across $N$ workers, each processes a different data batch.
- **AllReduce operation**: Sum gradients from all workers and broadcast result to all workers.
- Traffic pattern: All-to-all communication, bandwidth: $O(N \cdot M)$ where $M$ is model size.

**Model Parallelism**:
- Model partitioned across workers, each computes portion of the model.
- Traffic pattern: Pipelined activations and gradients between adjacent model stages.

**Parameter Server Architecture**:
- Centralized parameter servers aggregate gradients from workers.
- Traffic pattern: Many-to-one (workers → PS) and one-to-many (PS → workers), creates incast.

**Ring-AllReduce**:
- Workers arranged in logical ring, each communicates with two neighbors.
- Traffic pattern: Structured peer-to-peer, $2(N-1)$ communication rounds.
- Bandwidth-optimal: Each link transmits exactly once per element.

#### 2.1.4 Network Congestion Phenomena

**Incast Congestion**:
- Occurs when many senders simultaneously transmit to a single receiver.
- Causes: Queue overflow, packet drops, TCP timeouts.
- **Particularly severe in AI training**: Synchronized gradient aggregation creates predictable incast events.

**Queue Buildup**:
- Packets arrive faster than link can drain, accumulating in switch buffers.
- Increases latency proportional to queue occupancy: $\text{delay} = \frac{\text{queue\_length}}{\text{link\_rate}}$.
- **Bufferbloat**: Excessive buffering causes high latency without increasing throughput.

**TCP Incast Collapse**:
- Multiple synchronized TCP flows cause severe throughput degradation.
- Retransmission timeout (RTO) can be 100-1000× larger than RTT.
- **Mitigation**: ECN, DCTCP, fine-tuned TCP parameters, packet pacing.

### 2.2 Use Cases and Key Performance Indicators

#### 2.2.1 AI/ML Training Use Cases

**Large Language Model (LLM) Training**:
- Models: GPT-3 (175B params), BERT, T5, LLaMA.
- Communication: Periodic gradient AllReduce (every 100-500ms).
- **Requirements**: Low tail latency (<10ms P99), high throughput (>80% link utilization).
- **Failure mode**: Network stragglers delay iteration, reduce GPU utilization.

**Computer Vision Model Training**:
- Models: ResNet, Vision Transformers (ViT), YOLO.
- Smaller model size than LLMs but higher iteration frequency.
- **Requirements**: Predictable latency, efficient all-reduce.

**Recommendation Systems**:
- Models: DLRM (Deep Learning Recommendation Model), embedding tables.
- Communication: Embedding lookups, parameter server traffic.
- **Pattern**: Heavy many-to-one traffic to embedding servers.

**Hyperparameter Tuning and NAS**:
- Multiple concurrent training jobs with different hyperparameters.
- **Requirements**: Fair bandwidth sharing, interference isolation.

#### 2.2.2 Key Performance Indicators (KPIs)

**Flow Completion Time (FCT)**:
- Time from first packet sent to last ACK received.
- **Critical metric**: Directly impacts training iteration time.
- **Tail FCT** (P95, P99): More important than average due to synchronous training.
- **Goal**: Minimize P99 FCT to reduce stragglers.

**Link Utilization Balance**:
- Measures evenness of traffic distribution across parallel paths.
- **Formula**: $\text{Balance} = 1 - \frac{\sigma}{\mu}$ where $\sigma$ is std dev, $\mu$ is mean utilization.
- **Range**: [0, 1], higher is better (1 = perfect balance).
- **Goal**: >0.85 balance score, avoiding hotspots.

**Throughput**:
- Aggregate bits transmitted per second across all flows.
- **Goodput**: Successfully delivered application-layer data (excluding retransmissions).
- **Bisection throughput**: Aggregate bandwidth between halves of the network.
- **Goal**: >90% of theoretical maximum bisection bandwidth.

**Congestion Duration**:
- Time intervals where queue occupancy exceeds threshold (e.g., >80% buffer capacity).
- **Packet drop rate**: Percentage of packets dropped due to buffer overflow.
- **Goal**: Minimize congestion events, <1% packet drop rate.

**Latency Metrics**:
- **Round-Trip Time (RTT)**: Time for packet + ACK.
- **Queuing delay**: Time spent in switch buffers.
- **Tail latency**: P95/P99/P99.9 percentiles.
- **Goal**: P99 RTT <10ms for intra-DC traffic.

**Load Imbalance Factor**:
- $\text{Imbalance} = \frac{\max(\text{path\_util})}{\text{avg}(\text{path\_util})}$
- **Ideal value**: 1.0 (perfect balance).
- **ECMP typical**: 1.5-2.5 under AI workloads.
- **Adaptive target**: <1.3.

### 2.3 Literature Survey

#### Paper 1: CONGA - Distributed Congestion-Aware Load Balancing for Datacenters

**Reference**: Alizadeh et al., "CONGA: Distributed Congestion-Aware Load Balancing for Datacenters," ACM SIGCOMM 2014.

**Key Contributions**:
- Distributed congestion-aware load balancing using flowlet switching.
- **Congestion metric**: Remote congestion extent (CE) propagated via feedback.
- Each switch maintains per-path congestion estimates, updated using packet headers.
- Demonstrated 5× improvement in tail FCT over ECMP under realistic workloads.

**Relevance to Our Work**:
- Validates flowlet switching as viable approach for dynamic load balancing.
- Provides methodology for measuring and reacting to congestion.
- Congestion feedback mechanism inspires our monitoring approach.

**Limitations**:
- Requires custom switch hardware for CE tracking and feedback.
- Complex distributed coordination may cause transient instability.

#### Paper 2: HPCC - High Precision Congestion Control

**Reference**: Li et al., "HPCC: High Precision Congestion Control," ACM SIGCOMM 2019.

**Key Contributions**:
- INT (In-band Network Telemetry) for precise congestion measurement.
- Calculates inflight bytes using per-packet timestamp and rate information.
- Achieves near-zero queuing with high utilization (>95%).
- Specifically designed for RDMA/RoCE networks in AI clusters.

**Relevance to Our Work**:
- Emphasizes importance of precise congestion signals for AI workloads.
- INT-based monitoring provides inspiration for our real-time congestion tracking.
- Demonstrates that zero-queue, high-throughput operation is achievable.

**Limitations**:
- Requires programmable switches supporting INT.
- Focused on congestion control (rate limiting) rather than routing.

#### Paper 3: LetFlow - A Scalable and Practical Load Balancing Scheme

**Reference**: Vanini et al., "LetFlow: A Scalable and Practical Load Balancing Scheme," CoNEXT 2017.

**Key Contributions**:
- **Packet-level load balancing** using network-wide congestion view.
- Per-packet path selection (no flowlet detection needed).
- Uses switch queue lengths as congestion signal.
- Implemented on commodity switches using OpenFlow.

**Relevance to Our Work**:
- Demonstrates feasibility of adaptive routing on SDN switches.
- OpenFlow implementation strategy directly applicable to our Mininet setup.
- Queue-based congestion metric aligns with our monitoring approach.

**Limitations**:
- Per-packet forwarding risks packet reordering (requires receiver-side reordering).
- Control plane overhead for frequent path updates.

#### Paper 4: DRILL - Dynamic Routing and Intelligent Load Balancing

**Reference**: Ghorbani et al., "DRILL: Micro Load Balancing for Low-latency Data Center Networks," ACM SIGCOMM 2017.

**Key Contributions**:
- **Local** load balancing without global coordination.
- Random path selection weighted by local queue lengths.
- Extremely low overhead, no control plane.
- Reduces median FCT by 35% and P99 by 40% vs. ECMP.

**Relevance to Our Work**:
- Simplicity and low overhead align with practical deployment constraints.
- Empirical validation of queue-based load metrics.
- Demonstrates that even simple adaptive schemes significantly outperform ECMP.

**Limitations**:
- Random selection with local info may not find globally optimal paths.
- Requires hardware support for queue length exposure.

#### Paper 5: DCTCP - Data Center TCP

**Reference**: Alizadeh et al., "Data Center TCP (DCTCP)," ACM SIGCOMM 2010.

**Key Contributions**:
- Leverages ECN for early congestion signaling.
- Proportional rate reduction based on extent of congestion.
- Achieves high burst tolerance with low latency.
- **Critical enabler**: Complementary to adaptive routing; transport + routing synergy.

**Relevance to Our Work**:
- ECN marks serve as congestion signal for path selection.
- Understanding DCTCP behavior helps interpret traffic generation results.
- Highlights importance of cross-layer optimization (L3 routing + L4 transport).

**Limitations**:
- Requires ECN-capable switches and endpoints.
- Single queue cannot fully exploit multi-path diversity.

### 2.4 Current Challenges and Limitations

#### 2.4.1 Scalability Challenges

**State Overhead**:
- Per-flow state in flowlet tables grows with number of concurrent flows.
- AI training with 1000 workers × 1000 workers = $10^6$ concurrent flows.
- **Challenge**: Maintaining flowlet state in fast switch memory (TCAM/SRAM).

**Measurement Overhead**:
- Real-time link utilization monitoring requires frequent polling.
- Per-link statistics collection (packet counts, byte counts, drops).
- **Tradeoff**: Monitoring frequency vs. control plane load.

**Update Frequency**:
- Congestion state changes rapidly (millisecond timescales).
- Routing decisions must react quickly to avoid persistent congestion.
- **Challenge**: Balancing responsiveness vs. stability (avoiding oscillations).

#### 2.4.2 Packet Reordering

**Problem**:
- Different paths have different delay (queuing + propagation).
- Packets taking different paths may arrive out of order.
- TCP interprets reordering as loss, triggers unnecessary retransmissions.

**Solutions**:
- **Flowlet switching**: Natural idle gaps allow queue draining, minimizing reordering.
- **Receiver-side reordering**: Buffers and resequences packets (adds latency).
- **MPTCP**: Multipath TCP handles reordering natively.

**Trade-off**:
- Strict in-order delivery → limits load balancing granularity (must use large flowlets).
- Aggressive load balancing → packet reordering degrades TCP performance.

#### 2.4.3 Hardware Limitations

**Commodity Switch Constraints**:
- Limited programmability (OpenFlow, P4 on select devices).
- Shallow buffers (few MB), insufficient for large incast bursts.
- **Queue visibility**: Not all switches expose real-time queue lengths to control plane.

**ECMP Hardware Support**:
- ECMP is hardware-accelerated (line-rate performance).
- Adaptive routing often requires software data path or SmartNIC offload (lower performance).
- **Deployment friction**: Operators hesitant to deploy custom solutions.

#### 2.4.4 AI Workload Characteristics

**Synchronized Arrivals**:
- Gradient synchronization creates highly correlated traffic.
- All workers finish computation simultaneously, start network transfer together.
- **Problem**: Violates independence assumption of hash-based load balancing.

**Elephant vs. Mice Flows**:
- AI training: mostly elephant flows (large gradient tensors).
- ECMP performs poorly when hash collides two elephant flows on same path.
- **Requirement**: Flow-size aware load balancing.

**Iteration Time Sensitivity**:
- Network delay directly impacts GPU utilization (GPUs idle waiting for network).
- 10ms additional network latency → 1% slowdown in training.
- **Economic impact**: 1% slowdown on $10M GPU cluster = $100K wasted compute/year.

#### 2.4.5 Lack of Deployment Incentives

**Operational Complexity**:
- ECMP is well-understood, debuggable, supported by vendors.
- Adaptive routing adds complexity: monitoring infrastructure, state management, failure handling.
- **Barrier**: Network operators prioritize stability over marginal performance gains.

**Incremental Deployment**:
- Cannot deploy adaptive routing on subset of switches (requires network-wide support).
- **Challenge**: All-or-nothing upgrade prevents gradual rollout.

**Quantifying ROI**:
- Difficult to measure impact of network improvements on end-to-end training time.
- Many confounding factors (framework efficiency, optimizer choice, hardware).
- **Needed**: Clear benchmarks demonstrating cost/benefit of adaptive routing.

---

<div style="page-break-after: always;"></div>

## 3. Problem Framing

### 3.1 Specific Problem Statement

**Primary Research Question:**  
How can adaptive, congestion-aware routing improve network performance for synchronized all-to-all AI training traffic compared to traditional ECMP routing in leaf-spine data center fabrics?

**Specific Problems Addressed:**

1. **Load Imbalance Under Hash Collisions**:
   - ECMP's static hashing causes correlated flows to collide on the same path when hash(flow_A) mod k = hash(flow_B) mod k.
   - **Problem**: Under all-to-all traffic with N nodes, $\binom{N}{2}$ flows hashed to $k$ paths creates clustering.
   - **Impact**: Some paths overloaded (>95% utilization, packet drops) while others underutilized (<50%).

2. **Congestion Unawareness**:
   - ECMP forwards packets to pre-selected path regardless of current congestion state.
   - **Problem**: Once packets enter congested path, they experience high queuing delay and potential drops.
   - **Impact**: Tail latency increases by 5-10× during congestion events.

3. **Incast Susceptibility in Parameter Synchronization**:
   - AllReduce and parameter server patterns create periodic many-to-one traffic surges.
   - **Problem**: ECMP cannot adapt routing to spread incast traffic temporally or spatially.
   - **Impact**: Queue overflow, packet drops, TCP retransmission timeouts (200ms-1s).

4. **Inflexibility to Dynamic Conditions**:
   - Network conditions change due to failures, background traffic, multi-tenant interference.
   - **Problem**: ECMP's static routing cannot redistribute load when paths fail or become congested.
   - **Impact**: Reduced effective bisection bandwidth, degraded performance.

**Hypothesis:**  
Adaptive routing using flowlet-based path selection with real-time congestion awareness will:
- Reduce P99 flow completion time by **25-40%** compared to ECMP.
- Improve link utilization balance score from **~0.6 (ECMP)** to **>0.85 (Adaptive)**.
- Reduce congestion duration and packet drop rate by **50-70%**.
- Increase aggregate throughput by **15-30%** under high load conditions.

### 3.2 Scope and Assumptions

#### 3.2.1 In Scope

**Network Topology**:
- Leaf-spine architecture with configurable number of spines (2-8), leaves (2-8), hosts per leaf (2-8).
- Full mesh connectivity between leaves and spines.
- Homogeneous link capacities (1 Gbps or 10 Gbps).

**Routing Strategies**:
- **Baseline**: ECMP with 5-tuple hashing.
- **Adaptive**: Flowlet-based routing with congestion-aware path selection.
- **Comparison**: Side-by-side performance evaluation under identical traffic.

**Traffic Patterns**:
- All-to-all communication (simulating AllReduce operation).
- Configurable flow size, duration, and intensity.
- Synchronized start times (mimicking training iteration boundaries).

**Performance Metrics**:
- Flow completion time (mean, median, P95, P99).
- Link utilization (per-link, aggregate, balance score).
- Congestion metrics (queue occupancy, drop rate, congestion duration).
- Throughput (per-flow, aggregate, bisection).

**Implementation Platform**:
- Mininet for network emulation.
- Open vSwitch for SDN-based routing.
- iperf3 for traffic generation.
- Python for control plane and analysis.

#### 3.2.2 Out of Scope

**Physical Hardware**:
- No deployment on production data center switches.
- No specialized ASIC/FPGA-based forwarding.

**Transport Layer Optimizations**:
- Using standard TCP (not DCTCP, MPTCP, or RDMA).
- No priority queueing or explicit congestion notification (ECN).

**Application-Layer Optimizations**:
- Not integrating with actual ML frameworks (TensorFlow, PyTorch).
- No gradient compression, quantization, or sparsification.

**Multi-Tenancy**:
- Single-tenant environment (no competing applications).
- No QoS, traffic isolation, or bandwidth reservation.

**Failure Scenarios**:
- Assuming all links and switches operational (no link failures, switch crashes).
- Not evaluating failure recovery or rerouting time.

#### 3.2.3 Key Assumptions

1. **Symmetric Traffic**: All-to-all pattern assumes uniform data exchange between all node pairs (valid for data-parallel AllReduce).

2. **Flowlet Detection**: Assumes bursty traffic with natural idle gaps >50ms (realistic for AI training with CPU computation phase between network phases).

3. **Measurement Accuracy**: Assumes accurate, timely link utilization monitoring (1-second polling interval).

4. **No Background Traffic**: Dedicated network for AI training (no interfering flows).

5. **Homogeneous Endpoints**: All hosts have identical network interfaces and performance characteristics.

6. **Simplified Congestion Model**: Uses link utilization as proxy for congestion (ignores buffer dynamics, queuing models).

### 3.3 Timeliness and Importance

#### 3.3.1 Why Now?

**Explosion of AI Model Scale**:
- Model parameter counts doubling every 6-12 months (Scaling laws: Kaplan et al. 2020).
- GPT-3 (2020): 175B params → GPT-4 (2023): ~1.7T params → Future models: >10T params.
- **Implication**: Network traffic scales linearly with model size; communication bottleneck intensifies.

**GPU Performance Outpacing Network**:
- GPU FLOPS growing faster than network bandwidth (NVIDIA DGX H100: 32 PetaFLOPS compute, but only 3.2 Tbps network).
- **Gap**: Compute/Communication ratio increasing, making network efficiency critical.

**Economic Pressure**:
- AI training clusters cost $100M-$500M (Meta's RSC: 16,000 GPUs, estimated $300M).
- **Incentive**: 10% network efficiency improvement → $30M savings or faster time-to-model.

**Commoditization of RDMA**:
- InfiniBand and RoCE v2 becoming standard in AI data centers.
- **Opportunity**: High-performance transport enables focus on routing layer optimization.

#### 3.3.2 Industry Relevance

**Major Cloud Providers**:
- **Google TPU Pods**: Custom network topology and routing for TensorFlow workloads.
- **Amazon EC2 UlaClusters**: 100 Gbps EFA interconnect optimized for ML.
- **Microsoft Azure NDv5**: InfiniBand-based AI infrastructure.
- **Meta OCP**: Open Compute Project defining standards for AI networking.

**Rising Importance of Network in MLSys Research**:
- MLSys conferences: increasing papers on network-aware distributed training.
- **Examples**: BytePS, Blink, PipeDream, Megatron-LM all address communication efficiency.

**Sustainability Concerns**:
- Training GPT-3 consumes ~1,287 MWh (Strubell et al. 2019).
- **Impact**: Reducing training time reduces energy consumption and carbon footprint.

#### 3.3.3 Scientific Contribution

**Validation of Flowlet Switching for AI**:
- Prior work (CONGA, DRILL) evaluated on web workloads.
- **Gap**: Limited empirical studies on AI-specific traffic patterns.
- **Contribution**: Demonstrates effectiveness specifically for all-to-all synchronous patterns.

**Open-Source Simulation Framework**:
- Reproducible Mininet-based testbed for networking researchers.
- **Impact**: Enables rapid prototyping of new routing algorithms.

**Quantitative Performance Bounds**:
- Establishes baseline performance expectations for ECMP vs. Adaptive.
- **Value**: Informs cost/benefit analysis for production deployment.

### 3.4 Expected Key Performance Indicators

#### 3.4.1 Primary KPIs

**1. Tail Flow Completion Time (P99 FCT)**

- **Definition**: 99th percentile time for flows to complete transmission.
- **Measurement**: Track start time (first packet sent) to end time (final ACK received) for each flow.
- **Target**: 
  - ECMP baseline: ~50-80ms (for 1GB flows at 1Gbps with congestion).
  - Adaptive: <40ms (25-40% improvement).
- **Why It Matters**: P99 FCT directly impacts training iteration time; stragglers delay synchronization.

**2. Link Utilization Balance Score**

- **Definition**: $\text{Balance} = 1 - \frac{\sigma_{\text{util}}}{\mu_{\text{util}}}$ across parallel paths.
- **Measurement**: Sample per-link transmitted bytes every 1 second, compute variance.
- **Target**:
  - ECMP baseline: 0.55-0.65 (moderate imbalance).
  - Adaptive: >0.85 (good balance).
- **Why It Matters**: Imbalance wastes network capacity; underutilized paths represent missed opportunity.

**3. Aggregate Throughput**

- **Definition**: Total bits successfully delivered per second across all flows.
- **Measurement**: Sum of received throughput from all iperf3 clients.
- **Target**:
  - ECMP baseline: 60-70% of theoretical bisection bandwidth.
  - Adaptive: 80-90% of theoretical maximum.
- **Why It Matters**: Higher throughput → shorter training time per iteration.

#### 3.4.2 Secondary KPIs

**4. Congestion Duration**

- **Definition**: Total time any link experiences >80% utilization.
- **Measurement**: Integrate time intervals where $\text{link\_util}(t) > 0.8$.
- **Target**:
  - ECMP baseline: 40-60% of experiment duration.
  - Adaptive: <20% of duration (50-70% reduction).
- **Why It Matters**: Persistent congestion causes packet drops and retransmissions.

**5. Packet Drop Rate**

- **Definition**: Percentage of packets dropped due to buffer overflow.
- **Measurement**: $(tx\_packets - rx\_packets) / tx\_packets \times 100\%$.
- **Target**:
  - ECMP baseline: 2-5% (moderate drops under congestion).
  - Adaptive: <0.5% (minimal drops).
- **Why It Matters**: Drops trigger retransmissions, increasing FCT.

**6. Path Imbalance Factor**

- **Definition**: $\text{Imbalance} = \max(\text{path\_util}) / \text{mean}(\text{path\_util})$.
- **Measurement**: Compute maximum and mean utilization across spine uplinks.
- **Target**:
  - ECMP baseline: 1.8-2.5 (severe hotspots).
  - Adaptive: <1.3 (minor variation).
- **Why It Matters**: Quantifies worst-case hotspot severity.

#### 3.4.3 Success Criteria

The project will be considered successful if the adaptive routing scheme achieves:

1. **≥25% reduction** in P99 flow completion time vs. ECMP.
2. **≥0.30 increase** in link utilization balance score (e.g., 0.60 → 0.90).
3. **≥15% increase** in aggregate throughput.
4. **≥50% reduction** in congestion duration.
5. **Statistically significant differences** (p < 0.05) across multiple experimental runs.

#### 3.4.4 Experimental Methodology

**Topology Configuration**:
- 4 spine switches, 4 leaf switches, 4 hosts per leaf (16 total hosts).
- 1 Gbps links, 1 ms propagation delay.
- Full mesh (each leaf connected to all 4 spines).

**Traffic Generation**:
- All-to-all communication: each host sends 1 GB to every other host (15 flows per host, 240 total flows).
- Flow start synchronized to simulate training iteration boundary.
- Duration: 30-60 seconds per run.

**Experimental Runs**:
- 10 runs per configuration (ECMP, Adaptive) for statistical significance.
- Randomize flow ordering to avoid bias.

**Data Collection**:
- Per-flow FCT from iperf3 logs.
- Per-link statistics from Open vSwitch (tx_packets, tx_bytes, drops).
- Monitoring samples every 1 second.

**Analysis**:
- Compute percentiles (P50, P95, P99) for FCT.
- Calculate balance score and imbalance factor for utilization.
- Plot CDFs, box plots, and time-series graphs.
- Statistical tests: Wilcoxon rank-sum test for comparing ECMP vs. Adaptive.

---

