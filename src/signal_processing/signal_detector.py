# src/signal_processing/signal_detector.py

import time
import os
import sys
import pandas as pd
from threading import Thread
from rtlsdr import RtlSdr
import scapy.all as scapy
from scapy.layers.dot11 import Dot11Beacon, Dot11Elt, Dot11



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


#WIFI SIGNAL ANALYSIS / SNIFFING
#Found trackerjacker library, could be very useful
#Below code sniffs packets and analyzes them, returning detected WiFi networks including
#information such as MAC Address, Name, # of Channels, Signal Strength

if sys.version_info < (3, 0):
    sys.stderr.write("\nYou need python 3.0 or later to run this script\n")
    sys.stderr.write("Please update and make sure you use the command python3 wifi_scanner.py <interface>\n\n")
    sys.exit(0)

networks = pd.DataFrame(columns=["BSSID", "SSID", "dBm_Signal", "Source", "Destination", "Channel", "Encryption"])
networks.set_index("BSSID", inplace=True)

def process_packet(packet):
    """this function get executed whenever a packet is sniffed to process it"""
    if packet.haslayer(Dot11Beacon):
        bssid = packet[Dot11].addr2  # get the MAC addresses of the networks
        source = packet[Dot11].src #Get source IP address
        dest = packet[Dot11].dst #Get destination IP address
        ssid = str(packet[Dot11Elt].info, encoding="UTF-8")  # get the name of the networks
        ssid = "<Hidden>" if ssid == "" else str(packet[Dot11Elt].info, encoding="UTF-8")  # check if the network
        # doesn't broadcast its name (ternary operator)
        dbm_signal = packet.dBm_AntSignal  # get the signal strength of the networks

        stats = packet[Dot11Beacon].network_stats()  # extract network stats <channel, rate, encryption, etc..>
        channel = stats.get("channel")  # get the channel number of the networks
        enc = stats.get("crypto")  # get the encryption of the networks

        networks.loc[bssid] = (ssid, dbm_signal, source, dest, channel, enc)  # putting all together

def print_networks():
    """this function clear terminal every 0.7s and print wi-fi networks again"""
    while True:
        os.system("clear")
        print(networks)
        time.sleep(0.7)
