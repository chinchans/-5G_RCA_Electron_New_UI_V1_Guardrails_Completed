Certainly! Based on the provided dataset describing LTE/5G NSA attach and detach test procedures with a single UE, including detailed KPI requirements, signalling flows, and test environment setups, here is a comprehensive performance testing plan tailored for validating E2E O-RAN control plane functionality for LTE and 5G NSA attach-detach procedures.

---

# Comprehensive Performance Testing Plan for LTE/5G NSA Attach-Detach Procedures

---

## 1. Performance Requirements Analysis

### 1.1 Performance Objectives and SLAs
- **Attach Success Rate:** 100% success rate for attach procedure over 10 consecutive iterations.
- **Detach Success Rate:** 100% success rate for detach procedure over 10 consecutive iterations.
- **Secondary Node Addition/Release Success Rate:** 100% success for 5G NSA secondary node addition and release procedures.
- **Attach Latency:** Measure and report minimum, average, and maximum attach latency per 10 iterations. Targets to be defined by project or vendor KPIs.
- **Radio Quality:** Maintain excellent radio conditions as per Clause 4.6 (LTE RSRP or 5G SS-RSRP).
- **SLA:** The system shall sustain 10 consecutive attach-detach cycles without failures or errors under excellent radio conditions.
- **System Stability:** No connectivity issues during the attach-detach cycles.
- **Signalling Integrity:** Signalling flows as per 3GPP TS 23.401 and TS 37.340 must be validated for correctness and completeness.

### 1.2 Key Performance Indicators (KPIs)
- Attach Success Rate (%)
- Detach Success Rate (%)
- Secondary Node Addition Success Rate (5G NSA only)
- Secondary Node Release Success Rate (5G NSA only)
- Attach Latency (ms): Min, Avg, Max
- Radio Parameters: LTE RSRP, RSRQ; 5G SS-RSRP
- Signalling Message Validation (attach request/complete, detach request/accept, SgNB addition/release messages)
- UE Context Release and RRC Connection Release confirmation

### 1.3 Performance Baselines and Benchmarks
- Baselines to be established from initial test runs in excellent radio conditions.
- Attach Latency baseline benchmarked against vendor or 3GPP recommended thresholds.
- Success rates baseline: 100% over 10 iterations.
- Radio parameters baseline: LTE/5G RSRP and RSRQ as per Clause 4.6 (excellent conditions).

---

## 2. Test Strategy and Approach

### 2.1 Load Testing Scenarios
- Single UE attach-detach repeated 10 times under excellent radio conditions.
- Validate attach and detach success and latency.
- Include both LTE and 5G NSA scenarios.
- For 5G NSA, validate secondary node addition and release flows.

### 2.2 Stress and Volume Testing
- **Stress Testing:** Increase attach-detach frequency beyond normal to identify system limits.
- **Volume Testing:** Though single UE scenario is primary, test with multiple sequential UEs attaching/detaching to explore system scalability (if applicable).
- Test with degraded radio conditions to evaluate robustness and failure modes.

### 2.3 Performance Test Types
- **Load Test:** 10 iterations of attach-detach under excellent radio conditions.
- **Stress Test:** Rapid attach-detach cycles exceeding typical usage to stress network.
- **Spike Test:** Sudden bursts of attach requests to validate system response.
- **Endurance Test:** Extended duration test to monitor stability over time (e.g., continuous attach-detach cycles for hours/days).

---

## 3. Test Environment Setup

### 3.1 Hardware and Software Requirements
- Single isolated cell (O-RU + O-DU + O-CU) with LTE and 5G NSA capabilities.
- UE: Real or UE emulator capable of LTE and 5G NSA attach-detach.
- RF shielded environment or cable connection to maintain excellent radio conditions.
- Variable attenuator or fading generator to emulate radio conditions if needed.
- Logging and trace capture systems for call flow and signalling messages.

### 3.2 Test Data Requirements
- UE configuration data (PCI, Global eNB/gNB ID, ARFCN/NR-ARFCN).
- Attach-detach configuration parameters.
- Test configuration parameters recorded for each test run.
- Data forwarding addresses and bearer configurations for secondary node release.

### 3.3 Monitoring and Measurement Tools
- Signalling message capture tools (e.g., Wireshark, specialized 3GPP protocol analyzers).
- Radio parameter measurement tools for RSRP, RSRQ.
- Timing measurement tools for latency computations.
- System monitoring tools for CPU, memory, and network resource usage.
- Alerting system for failures or anomalies.

---

## 4. Test Scenarios and Scripts

### 4.1 Realistic User Scenarios
- Scenario 1: UE powers ON, performs LTE attach, remains connected briefly, then powers OFF to detach. Repeat 10 times.
- Scenario 2: UE powers ON, performs 5G NSA attach including secondary node addition, then powers OFF to trigger detach and secondary node release. Repeat 10 times.
- Scenario 3 (Stress): Rapid attach-detach cycles to test limits.
- Scenario 4 (Endurance): Continuous attach-detach cycles over extended period.

### 4.2 Test Data Sets
- UE identities and cell parameters matching lab or field environment.
- Variations in ARFCN/NR-ARFCN to verify correct cell attachment.
- Radio condition parameters for excellent and degraded scenarios.

### 4.3 Performance Test Scripts
- Automated scripts to:
  - Power ON UE.
  - Wait for attach complete message.
  - Log attach latency.
  - Power OFF UE.
  - Wait for detach complete message.
  - Validate signalling flows and message correctness.
  - Repeat for 10 iterations.
- Scripts to capture and log radio parameters and KPIs.
- Scripts for 5G NSA secondary node addition and release validation.

---

## 5. Performance Metrics and Monitoring

### 5.1 Key Metrics to Measure
- Attach success/failure counts and percentage.
- Detach success/failure counts and percentage.
- Secondary node addition and release success/failure (5G NSA).
- Attach latency per iteration (min, avg, max).
- Radio parameters (RSRP, RSRQ).
- Signalling message completeness and correctness.
- System resource utilization during tests.

### 5.2 Monitoring and Alerting
- Real-time monitoring dashboards for KPIs.
- Alerts on failure rates exceeding thresholds.
- Notifications for latency exceeding targets.
- Anomaly detection for unusual signalling behavior.

### 5.3 Performance Data Collection
- Capture logs for all signalling messages.
- Store latency and success metrics in structured format.
- Record radio parameters alongside attach-detach events.
- Maintain test configuration snapshots for traceability.

---

## 6. Analysis and Reporting

### 6.1 Performance Analysis Procedures
- Validate KPIs against expected 100% success rates and latency targets.
- Analyze attach and detach signalling flows for compliance with 3GPP TS 23.401 and TS 37.340.
- Correlate radio parameters with attach-detach success and latency.
- Perform gap analysis comparing measured KPIs vs target SLAs.
- Identify patterns or intermittent failures.

### 6.2 Reporting Formats and Frequency
- Summary report per test run including:
  - Test configuration details.
  - KPIs: attach/detach success rates, latencies, radio parameters.
  - Signalling flow compliance.
  - Anomalies and failures with root cause analysis.
- Frequency:
  - After each test campaign.
  - Interim reports for long endurance or stress tests.
  - Final comprehensive report including recommendations.

### 6.3 Performance Optimization Recommendations
- Based on analysis, recommend:
  - Radio condition improvements.
  - Network parameter tuning (e.g., timers, retransmission).
  - UE or network firmware upgrades.
  - Enhancements in secondary node procedures.
  - Load balancing or capacity planning as needed.

---

## 7. Risk Mitigation

### 7.1 Identify Performance Risks
- Radio condition degradation causing attach/detach failures.
- Network resource exhaustion under stress.
- Signalling message loss or corruption.
- Secondary node release delays or failures.
- UE firmware or emulator bugs.
- Environmental interference in field tests.

### 7.2 Plan for Performance Bottlenecks
- Monitor resource utilization to pre-empt bottlenecks.
- Use controlled attenuation to avoid radio overload or underload.
- Validate signalling integrity with redundant captures.
- Include fallback procedures for secondary node failures.

### 7.3 Define Performance Degradation Handling
- Automated retry mechanisms in test scripts for transient failures.
- Immediate alerting and logging upon failures.
- Rollback to last known good configuration.
- Escalation procedures for unresolved issues.
- Documentation of degradation incidents for continuous improvement.

---

# Summary

This performance testing plan provides a structured approach to validate LTE and 5G NSA attach and detach procedures with a single UE, ensuring full compliance with 3GPP specifications and O-RAN requirements. By combining rigorous KPI measurement, realistic scenarios, and robust test environment setups, it delivers a comprehensive framework to guarantee system reliability and optimal performance under specified SLAs.

---

If you need, I can help prepare detailed test scripts or assist with specific tool recommendations for implementation.