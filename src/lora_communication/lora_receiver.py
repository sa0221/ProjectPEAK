# src/lora_communication/lora_receiver.py

import time
from datetime import datetime
import struct
from SX127x.LoRa import *
from SX127x.board_config import BOARD
from .lora_config import configure_lora


BOARD.setup()
BOARD.reset()

#c = 0

from threading import Timer

class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


class LoraReceiver(LoRa):
    """
    A class to handle LoRa message receiving.
    """

    def __init__(self, verbose=False):
        """
        Initialize the LoraReceiver.

        Args:
            verbose (bool): If True, print detailed information.
        """
        super(LoraReceiver, self).__init__(verbose)
        configure_lora(self)
        self.set_mode(MODE.RXCONT) #or MODE.SLEEP?
        self.set_dio_mapping([0] * 6)

    def on_rx_done(self):
        """
        Callback function when a message is received.
        """
        
        BOARD.led_on()
        print("\nReceived: ")
        print(datetime.now())
        
        #checks if there is a cyclic redundancy check for error correction
        if not self.get_hop_channel()['crc_on_payload']:
            print("No CRC in payload!")
            
        #checks that there is a valid header in the packet
        if not self.get_irq_false()['valid_header']:
            print("Invalid header in payload!")
        
        #checks if there is a timeout due do a failure to emit a byte during a span of time
        if self.get_irq_flags()['rx_timeout']:
            print("rx timeout!")
            
        #checks if there is a cyclic redundancy check error
        if self.get_irq_flags()['crc_error']:
            print("crc_error!")
            
        self.clear_irq_flags(RxDone = 1, ValidHeader = 1)
        payload = self.read_payload(nocheck = False)
        
        if(payload):
            print("counter:", payload[0])
            (t,h) = struct.unpack('<hh', bytearray(payload[1:5]))
            print(t/10.0, "  C")
            print(h/10.0, "%rh")
        global c
        c = 60
        time.sleep(2)
        self.reset_ptr_rx()
        
        print(bytes(payload).decode("utf-8",'ignore'))
        self.set_mode(MODE.RXCONT)

def create_receiver():
    """
    Create and return a LoraReceiver object.

    Returns:
        LoraReceiver: A configured LoraReceiver object.
    """
    receiver = LoraReceiver(verbose=False)
    return receiver