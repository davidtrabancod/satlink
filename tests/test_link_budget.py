import pytest
from satlink.core.link_budget import SatelliteTransmitter, GroundStationReceiver, LinkBudgetCalculator

def test_fspl_calculation():
    # Para d = 1000 km y f = 437.5 MHz (UHF Cubesat habitual)
    # FSPL ≈ 32.44 + 20*log10(1000) + 20*log10(437.5) = 32.44 + 60 + 52.82 = 145.26 dB
    fspl = LinkBudgetCalculator.calculate_fspl(range_km=1000.0, frequency_mhz=437.5)
    assert pytest.approx(fspl, 0.1) == 145.26

def test_link_budget_evaluation():
    tx = SatelliteTransmitter(frequency_mhz=437.5, tx_power_dbw=0.0, tx_antenna_gain_dbi=2.15) # 1W en dipolo
    rx = GroundStationReceiver(rx_antenna_gain_dbi=12.0, system_noise_temp_k=300.0, bandwidth_hz=12500.0) # Yagi 12 dBi, 12.5 kHz
    
    calc = LinkBudgetCalculator(tx, rx)
    result = calc.evaluate_link(range_km=800.0)
    
    assert "received_power_dbw" in result
    assert "cn_ratio_db" in result
    assert "link_margin_db" in result
    assert result["link_margin_db"] > 0.0  # Con estos parámetros en 800 km el enlace debe cerrar con margen positivo