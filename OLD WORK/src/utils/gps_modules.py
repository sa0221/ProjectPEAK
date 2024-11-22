# src/utils/gps_module.py

import serial
import pynmea2

class GPSModule:
    """
    A class to interface with the GT-U7 GPS Module (NEO-6M).
    """

    def __init__(self, port='/dev/ttyS0', baudrate=9600, timeout=1):
        """
        Initialize the GPS module.

        Args:
            port (str): Serial port to which the GPS module is connected.
            baudrate (int): Baud rate for serial communication.
            timeout (int): Read timeout in seconds.
        """
        self.ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)

    def get_position(self):
        """
        Get the current GPS position.

        Returns:
            dict: Dictionary with 'lat', 'lon', 'alt'.
        """
        while True:
            line = self.ser.readline().decode('ascii', errors='replace')
            if line.startswith('$GPGGA'):
                msg = pynmea2.parse(line)
                return {'lat': msg.latitude, 'lon': msg.longitude, 'alt': msg.altitude}
            elif line.startswith('$GNGGA'):
                msg = pynmea2.parse(line)
                return {'lat': msg.latitude, 'lon': msg.longitude, 'alt': msg.altitude}

    def close(self):
        """
        Close the serial connection.
        """
        self.ser.close()
