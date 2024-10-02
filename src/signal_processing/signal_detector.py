# src/signal_processing/signal_detector.py

import numpy as np
import time
from pyhackrf import HackRF

class SignalDetector:
    """
    A class to detect signals using HackRF One.
    """

    def __init__(self, freq, sample_rate=2.4e6, gain=40):
        """
        Initialize the SignalDetector.

        Args:
            freq (float): The center frequency in Hz.
            sample_rate (float): The sample rate in Hz.
            gain (int): The gain setting.
        """
        self.freq = freq
        self.sample_rate = sample_rate
        self.gain = gain
        self.hackrf = HackRF()
        self.configure_hackrf()

        # For RSSI timeseries
        self.rssi_timeseries = []

    def configure_hackrf(self):
        """
        Configure the HackRF One device.
        """
        self.hackrf.open()
        self.hackrf.set_sample_rate(self.sample_rate)
        self.hackrf.set_freq(self.freq)
        self.hackrf.set_amp_enable(True)
        self.hackrf.set_lna_gain(self.gain)
        self.hackrf.set_vga_gain(self.gain)

    def get_power_spectrum(self, num_samples=256*1024):
        """
        Get the power spectrum of the signal.

        Args:
            num_samples (int): Number of samples to read.

        Returns:
            tuple: Frequencies and power spectrum values.
        """
        samples = self.hackrf.read_samples(num_samples)
        # Compute the FFT and shift zero frequency component to center
        fft_samples = np.fft.fftshift(np.fft.fft(samples))
        power = np.abs(fft_samples) ** 2
        freqs = np.fft.fftshift(np.fft.fftfreq(len(samples), 1 / self.sample_rate))
        return freqs + self.freq, power

    def measure_signal_strength(self):
        """
        Measure the current signal strength.

        Returns:
            float: The signal strength in dB.
        """
        freqs, power = self.get_power_spectrum()
        max_power = 10 * np.log10(np.max(power))
        self.rssi_timeseries.append(max_power)
        return max_power

    def detect_signal(self, threshold=-50):
        """
        Detect the presence of a signal above a certain threshold.

        Args:
            threshold (float): Threshold for signal detection in dB.

        Returns:
            bool: True if signal is detected, False otherwise.
        """
        signal_strength = self.measure_signal_strength()
        if signal_strength > threshold:
            return True
        else:
            return False

    def get_rssi_timeseries(self):
        """
        Get the time series of RSSI measurements.

        Returns:
            list: List of RSSI values.
        """
        return self.rssi_timeseries

    def close(self):
        """
        Close the HackRF device.
        """
        self.hackrf.close()
