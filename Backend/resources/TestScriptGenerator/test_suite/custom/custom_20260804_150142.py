```python
import pytest

# Constants for 5G NR L1 throughput calculation as per 3GPP TS 38.214 Clause 6.1
# Throughput = (N_RE * N_symb * N_PRB * N_layers * modulation_order * code_rate) / T_slot
# Where:
# - N_RE: Number of resource elements per PRB per OFDM symbol (usually 12 subcarriers)
# - N_symb: Number of OFDM symbols used for PDSCH in a slot (depends on DMRS and overhead)
# - N_PRB: Number of allocated physical resource blocks
# - N_layers: Number of MIMO layers (1 to 8)
# - modulation_order: bits per symbol (QPSK=2, 16QAM=4, 64QAM=6, 256QAM=8)
# - code_rate: coding rate (0.0 < code_rate <= 1.0)
# - T_slot: slot duration in seconds (depends on subcarrier spacing)
#
# This formula calculates raw physical layer throughput in bits per second.
#
# Note: This simplified formula assumes full slot usage for PDSCH and ideal conditions.

def calculate_slot_duration(subcarrier_spacing_khz):
    # Number of slots per 10ms frame for given SCS
    # normal CP: T_slot = 1ms / 2^μ, μ=log2(SCS/15)
    # e.g. SCS=15kHz -> μ=0 -> T_slot=1ms
    # SCS=30kHz -> μ=1 -> T_slot=0.5ms
    # SCS=60kHz -> μ=2 -> T_slot=0.25ms
    import math
    mu = int(round(math.log2(subcarrier_spacing_khz / 15)))
    T_slot = 0.001 / (2 ** mu)  # in seconds
    return T_slot


@pytest.fixture
def default_params():
    return {
        "N_RE": 12,                    # 12 subcarriers per PRB
        "N_symb": 14,                  # full slot with 14 OFDM symbols (normal CP)
        "N_PRB": 50,                   # placeholder: 50 PRBs allocated
        "N_layers": 2,                 # 2 layers MIMO
        "modulation_order": 6,         # 64QAM modulation (6 bits per symbol)
        "code_rate": 0.75,             # coding rate 0.75
        "subcarrier_spacing_khz": 30  # 30 kHz SCS
    }


def calculate_l1_throughput(params):
    """
    Calculate L1 throughput in bits per second using 3GPP TS 38.214 Clause 6.1 formula.
    """
    N_RE = params["N_RE"]
    N_symb = params["N_symb"]
    N_PRB = params["N_PRB"]
    N_layers = params["N_layers"]
    modulation_order = params["modulation_order"]
    code_rate = params["code_rate"]
    subcarrier_spacing_khz = params["subcarrier_spacing_khz"]

    T_slot = calculate_slot_duration(subcarrier_spacing_khz)  # seconds per slot

    # Total bits per slot before coding
    bits_per_slot_uncoded = N_RE * N_symb * N_PRB * N_layers * modulation_order

    # Apply coding rate
    bits_per_slot_coded = bits_per_slot_uncoded * code_rate

    # Throughput = bits per slot / slot duration (bps)
    throughput_bps = bits_per_slot_coded / T_slot

    return throughput_bps


# Telecom realistic attach/detach placeholders and KPI check simulation
def perform_attach():
    """
    Simulate UE attach procedure.
    In real tests, this would involve RRC connection setup and NAS attach.
    Here, we mock success.
    """
    # Placeholder for attach steps
    return True


def perform_detach():
    """
    Simulate UE detach procedure.
    """
    # Placeholder for detach steps
    return True


def check_rrc_state(expected_state="CONNECTED"):
    """
    Simulate RRC state check.
    """
    # Placeholder: assume RRC is in expected state after attach
    return True


def check_kpi_throughput(throughput_bps, threshold_bps):
    """
    Check if throughput meets threshold KPI.
    """
    return throughput_bps >= threshold_bps


@pytest.mark.parametrize(
    "params",
    [
        # Typical 50 PRBs, 2 layers, 64QAM, code rate 0.75, 30kHz SCS
        {
            "N_RE": 12,
            "N_symb": 14,
            "N_PRB": 50,
            "N_layers": 2,
            "modulation_order": 6,
            "code_rate": 0.75,
            "subcarrier_spacing_khz": 30
        },
        # Edge case: minimal PRBs and QPSK
        {
            "N_RE": 12,
            "N_symb": 14,
            "N_PRB": 1,
            "N_layers": 1,
            "modulation_order": 2,
            "code_rate": 0.5,
            "subcarrier_spacing_khz": 15
        },
        # High order modulation and layers
        {
            "N_RE": 12,
            "N_symb": 14,
            "N_PRB": 100,
            "N_layers": 4,
            "modulation_order": 8,  # 256QAM
            "code_rate": 0.85,
            "subcarrier_spacing_khz": 60
        }
    ]
)
def test_l1_throughput_calculation(params):
    # Step 1: Perform attach (RRC + NAS)
    assert perform_attach(), "Attach procedure failed"

    # Step 2: Check RRC connected state
    assert check_rrc_state("CONNECTED"), "RRC not in CONNECTED state"

    # Step 3: Calculate throughput
    throughput_bps = calculate_l1_throughput(params)

    # Step 4: KPI check - expect throughput > 0 (basic sanity)
    assert throughput_bps > 0, "Calculated throughput should be positive"

    # Step 5: Check throughput against a realistic threshold (placeholder)
    # Example threshold: 10 Mbps (10_000_000 bps)
    threshold_bps = 10_000_000
    assert check_kpi_throughput(throughput_bps, threshold_bps), \
        f"Throughput {throughput_bps:.2f} bps below KPI threshold {threshold_bps} bps"

    # Step 6: Perform detach
    assert perform_detach(), "Detach procedure failed"
```