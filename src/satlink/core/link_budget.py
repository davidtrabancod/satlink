import numpy as np
from dataclasses import dataclass
from typing import Dict, Union

# Constantes físicas
C_SPEED = 299792458.0  # Velocidad de la luz (m/s)
BOLTZMANN_K = 1.380649e-23  # Constante de Boltzmann (J/K)
BOLTZMANN_K_DBW = -228.6  # 10 * log10(k) en dBW/(Hz*K)


@dataclass
class SatelliteTransmitter:
    frequency_mhz: float      # Frecuencia central de downlink (MHz)
    tx_power_dbw: float       # Potencia del transmisor del satélite (dBW)
    tx_antenna_gain_dbi: float # Ganancia de la antena transmisora (dBi)
    tx_losses_db: float = 1.0  # Pérdidas de acoplo/línea en el satélite (dB)

    @property
    def eirp_dbw(self) -> float:
        """Calcula la Potencia Isotrópica Radiada Equivalente (EIRP) en dBW."""
        return self.tx_power_dbw + self.tx_antenna_gain_dbi - self.tx_losses_db


@dataclass
class GroundStationReceiver:
    rx_antenna_gain_dbi: float  # Ganancia de la antena de la estación terrestre (dBi)
    system_noise_temp_k: float  # Temperatura de ruido del sistema Tsys (K)
    bandwidth_hz: float         # Ancho de banda del canal (Hz)
    rx_losses_db: float = 1.5   # Pérdidas de cable, apuntamiento y atmosféricas (dB)
    required_ebn0_db: float = 10.0 # Eb/N0 mínimo requerido por el módem/demodulador (dB)
    bit_rate_bps: float = None  # Tasa de bits (bps). Si es None, se asume Rb = Bandwidth


class LinkBudgetCalculator:
    def __init__(self, tx: SatelliteTransmitter, rx: GroundStationReceiver):
        self.tx = tx
        self.rx = rx

    @staticmethod
    def calculate_fspl(range_km: Union[float, np.ndarray], frequency_mhz: float) -> Union[float, np.ndarray]:
        """
        Calcula las pérdidas de propagación en espacio libre (FSPL) en dB.
        Acepta tanto un valor flotante como un array de NumPy de distancias.
        """
        return 32.44 + 20 * np.log10(range_km) + 20 * np.log10(frequency_mhz)

    def evaluate_link(self, range_km: Union[float, np.ndarray]) -> Dict[str, Union[float, np.ndarray]]:
        """
        Calcula el balance completo del radioenlace para una distancia o vector de distancias.
        """
        # 1. Pérdidas de espacio libre (FSPL)
        fspl_db = self.calculate_fspl(range_km, self.tx.frequency_mhz)

        # 2. Potencia Recibida (Pr)
        total_losses_db = fspl_db + self.rx.rx_losses_db
        pr_dbw = self.tx.eirp_dbw + self.rx.rx_antenna_gain_dbi - total_losses_db

        # 3. Densidad espectral de ruido (N0) y Potencia total de ruido (N)
        n0_dbw_hz = BOLTZMANN_K_DBW + 10 * np.log10(self.rx.system_noise_temp_k)
        noise_power_dbw = n0_dbw_hz + 10 * np.log10(self.rx.bandwidth_hz)

        # 4. Relación C/N
        cn_ratio_db = pr_dbw - noise_power_dbw

        # 5. Relación Eb/N0
        bit_rate = self.rx.bit_rate_bps if self.rx.bit_rate_bps else self.rx.bandwidth_hz
        ebn0_db = cn_ratio_db + 10 * np.log10(self.rx.bandwidth_hz / bit_rate)

        # 6. Margen de Enlace
        link_margin_db = ebn0_db - self.rx.required_ebn0_db

        return {
            "range_km": range_km,
            "fspl_db": np.round(fspl_db, 2),
            "eirp_dbw": round(self.tx.eirp_dbw, 2),
            "received_power_dbw": np.round(pr_dbw, 2),
            "noise_power_dbw": round(noise_power_dbw, 2),
            "cn_ratio_db": np.round(cn_ratio_db, 2),
            "ebn0_db": np.round(ebn0_db, 2),
            "link_margin_db": np.round(link_margin_db, 2)
        }