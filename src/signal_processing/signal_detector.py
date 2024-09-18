# src/signal_processing/signal_detector.py

import time
import numpy as np
from rtlsdr import RtlSdr

class SignalDetector:
    """
    A class to detect signals using RTL-SDR.
    """

    def __init__(self, freq, sample_rate=2.4e6, gain='auto'):
        """
        Initialize the SignalDetector.

        Args:
            freq (float): The center frequency in Hz.
            sample_rate (float): The sample rate in Hz.
            gain (str or float): The gain setting.
        """
        self.freq = freq
        self.sample_rate = sample_rate
        self.gain = gain
        self.sdr = RtlSdr()
        self.configure_sdr()

    def configure_sdr(self):
        """
        Configure the RTL-SDR device.
        """
        self.sdr.sample_rate = self.sample_rate
        self.sdr.center_freq = self.freq
        self.sdr.gain = self.gain

    def get_power_spectrum(self, num_samples=256*1024):
        """
        Get the power spectrum of the signal.

        Args:
            num_samples (int): Number of samples to read.

        Returns:
            tuple: Frequencies and power spectrum values.
        """
        samples = self.sdr.read_samples(num_samples)
        # Compute the FFT and shift zero frequency component to center
        fft_samples = np.fft.fftshift(np.fft.fft(samples))
        power = np.abs(fft_samples) ** 2
        freqs = np.fft.fftshift(np.fft.fftfreq(len(samples), 1 / self.sample_rate))
        return freqs + self.freq, power

    def detect_signal(self, threshold=1e6):
        """
        Detect the presence of a signal above a certain threshold.

        Args:
            threshold (float): Threshold for signal detection.

        Returns:
            bool: True if signal is detected, False otherwise.
        """
        freqs, power = self.get_power_spectrum()
        max_power = np.max(power)
        if max_power > threshold:
            return True
        else:
            return False

    def close(self):
        """
        Close the SDR device.
        """
        self.sdr.close()