```python
import pytest
import math

# Placeholder parameters for the L1 throughput calculation as per 3GPP 38.213 Clause 6.1 (assuming NR DL throughput)
# Formula reference (simplified):
# L1 Throughput (bps) = N_RE * Qm * code_rate * N_layers * (1 / TTI) 
# where:
# - N_RE = Number of resource elements used for PDSCH per TTI (depends on RBs, symbols, REs per RB)
# - Qm = modulation order (bits per symbol), e.g. 2 for QPSK, 4 for 16QAM, 6 for 64QAM, 8 for 256QAM
# - code_rate = transport block code rate (0 < code_rate <= 1)
# - N_layers = number of MIMO layers (1..8)
# - TTI = duration of the transmission time interval (seconds), typically 1 ms = 0.001s for NR slot in normal cyclic prefix

# We simulate realistic values for these parameters.

def calculate_l1_throughput(n_rbs, n_symbols, re_per_rb, q_m, code_rate, n_layers, tti_sec):
    """
    Calculate L1 throughput in bps for 5G NR as per Clause 6.1 formula.

    Args:
        n_rbs (int): Number of allocated Resource Blocks.
        n_symbols (int): Number of OFDM symbols used for PDSCH in one TTI.
        re_per_rb (int): Number of resource elements per RB per symbol (usually 12 subcarriers).
        q_m (int): Modulation order (bits per symbol).
        code_rate (float): Transport block code rate (0 < code_rate <=1).
        n_layers (int): Number of MIMO layers.
        tti_sec (float): Duration of TTI in seconds.

    Returns:
        float: L1 throughput in bits per second (bps).
    """
    n_re = n_rbs * n_symbols * re_per_rb  # Total resource elements used for PDSCH per TTI
    throughput = n_re * q_m * code_rate * n_layers / tti_sec
    return throughput


@pytest.fixture
def default_params():
    # Typical 5G NR parameters placeholders for test:
    params = {
        "n_rbs": 50,            # Number of RBs allocated in bandwidth (e.g. 10 MHz ~ 50 RBs)
        "n_symbols": 12,        # Number of OFDM symbols in a slot (normal CP)
        "re_per_rb": 12,        # 12 subcarriers per RB
        "q_m": 6,               # 64QAM modulation (6 bits per symbol)
        "code_rate": 0.75,      # Example coding rate (75%)
        "n_layers": 2,          # 2 MIMO layers
        "tti_sec": 0.001        # 1 ms slot duration
    }
    return params


def test_l1_throughput_calculation_basic(default_params):
    p = default_params
    throughput = calculate_l1_throughput(
        n_rbs=p["n_rbs"],
        n_symbols=p["n_symbols"],
        re_per_rb=p["re_per_rb"],
        q_m=p["q_m"],
        code_rate=p["code_rate"],
        n_layers=p["n_layers"],
        tti_sec=p["tti_sec"]
    )
    # Check throughput is positive and within reasonable expected range for NR 10 MHz with 64QAM and 2 layers
    assert throughput > 0
    # Rough upper bound: 50 RB * 12 sym * 12 RE * 6 bits * 1 * 2 layers / 0.001s = ~8.64 Gbps max (assuming code_rate=1)
    # With code_rate=0.75, expect ~6.48 Gbps max
    assert throughput < 9e9
    # Print for visibility (pytest capture can show with -s)
    print(f"Calculated L1 Throughput: {throughput / 1e6:.2f} Mbps")


def test_l1_throughput_with_various_modulation(default_params):
    p = default_params
    for q_m in [2, 4, 6, 8]:  # QPSK, 16QAM, 64QAM, 256QAM
        throughput = calculate_l1_throughput(
            n_rbs=p["n_rbs"],
            n_symbols=p["n_symbols"],
            re_per_rb=p["re_per_rb"],
            q_m=q_m,
            code_rate=p["code_rate"],
            n_layers=p["n_layers"],
            tti_sec=p["tti_sec"]
        )
        assert throughput > 0
        # Throughput increases with modulation order
        print(f"Modulation Qm={q_m}: Throughput={throughput/1e6:.2f} Mbps")


def test_l1_throughput_with_different_layers(default_params):
    p = default_params
    for layers in [1, 2, 4]:
        throughput = calculate_l1_throughput(
            n_rbs=p["n_rbs"],
            n_symbols=p["n_symbols"],
            re_per_rb=p["re_per_rb"],
            q_m=p["q_m"],
            code_rate=p["code_rate"],
            n_layers=layers,
            tti_sec=p["tti_sec"]
        )
        assert throughput > 0
        print(f"MIMO layers={layers}: Throughput={throughput/1e6:.2f} Mbps")


def test_l1_throughput_with_code_rate_edge_cases(default_params):
    p = default_params
    # Test code_rate boundaries
    for code_rate in [0.1, 0.5, 0.9, 1.0]:
        throughput = calculate_l1_throughput(
            n_rbs=p["n_rbs"],
            n_symbols=p["n_symbols"],
            re_per_rb=p["re_per_rb"],
            q_m=p["q_m"],
            code_rate=code_rate,
            n_layers=p["n_layers"],
            tti_sec=p["tti_sec"]
        )
        assert throughput > 0
        # code_rate must be <=1 and >0
        assert 0 < code_rate <= 1
        print(f"Code rate={code_rate}: Throughput={throughput/1e6:.2f} Mbps")


def test_l1_throughput_with_different_tti(default_params):
    p = default_params
    # Different TTI durations (e.g. mini-slot 0.5 ms, slot 1 ms)
    for tti in [0.0005, 0.001]:
        throughput = calculate_l1_throughput(
            n_rbs=p["n_rbs"],
            n_symbols=p["n_symbols"],
            re_per_rb=p["re_per_rb"],
            q_m=p["q_m"],
            code_rate=p["code_rate"],
            n_layers=p["n_layers"],
            tti_sec=tti
        )
        assert throughput > 0
        print(f"TTI duration={tti*1e3} ms: Throughput={throughput/1e6:.2f} Mbps")
```