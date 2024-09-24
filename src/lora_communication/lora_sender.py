# src/lora_communication/lora_sender.py

import sys
from time import sleep
from SX127x.LoRa import *
from SX127x.board_config import BOARD
from .lora_config import configure_lora
from SX127x.LoRaArgumentParser import LoRaArgumentParser

BOARD.setup()

parser = LoRaArgumentParser("LoRa sender.")

class LoraSender(LoRa):
    """
    A class to handle LoRa message sending.
    """

    def __init__(self, verbose=False):
        """
        Initialize the LoraSender.

        Args:
            verbose (bool): If True, print detailed information.
        """
        super(LoraSender, self).__init__(verbose)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([1,0,0,0,0,0]) #DIO0 = 1 = tx_done (0 = rx_done)
        #configure_lora(self)
        
    def on_rx_done(self):
        print("\nRxDone")
        print(self.get_irq_flags())
        print(map(hex, self.read_payload(nocheck = True)))
        self.set_mode(MODE.SLEEP)
        self.reset_ptr_rx()
        self.set_mode(MODE.RXCONT)

    def on_tx_done(self):
        """
        Callback function when transmission is done.
        """
        global args
        print("\nTxDone")
        self.set_mode(MODE.STDBY)
        self.clear_irq_flags(TxDone=1)
        sys.stdout.flush()
        self.tx_counter += 1
        sys.stdout.write("\rtx #%d" % self.tx_counter)
        BOARD.led_off()
        sleep(1)
        self.write_payload([0x0e,0x00,0x00,0x00,0x00,0x00])
        BOARD.led_on()
        self.set_mode(MODE.TX)
        sys.stdout.write("on_tx_done end")
        

    def send_message(self, message):
        """
        Send a message using LoRa.

        Args:
            message (str): The message to send.
        """
        self.write_payload(list(message.encode()))
        self.set_mode(MODE.TX)
        while (self.get_irq_flags()['tx_done'] == 0):
            sleep(0.1)
        self.clear_irq_flags(TxDone=1)

def create_sender():
    """
    Create and return a LoraSender object.

    Returns:
        LoraSender: A configured LoraSender object.
    """
    sender = LoraSender(verbose=False)
    args = parser.parse_args(lora) #configs in LoRaArgumentParser.py
    
    #lora.set_mode(MODE.STDBY)
    lora.set_pa_config(pa_select=1, max_power=21, output_power=2)
    lora.set_freq(868.0)
    lora.set_bw(BW.BW125)
    lora.set_spreading_factor(10)
    lora.set_sync_word(0x77)
    lora.set_rx_crc(True)
    #lora.set_rx_crc(False)
    return sender