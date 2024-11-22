# src/lora_communication/lora_config.py

from SX127x.LoRa import *
from SX127x.board_config import BOARD

BOARD.setup()

# LoRa configuration parameters
LORA_PARAMS = {
    'freq': 868,  # Frequency in MHz
    'spreading_factor': 7,
    'bandwidth': BW.BW125,
    'coding_rate': CODING_RATE.CR4_5,
    'power_mode': POWER_MODE.PA_BOOST,
    'tx_power': 17,
    'preamble': 8,
    'implicit_header': False,
    'sync_word': 0x12,
    'enable_CRC': True
}

def configure_lora(lora):
    """
    Configure the LoRa device with the specified parameters.
    
    Args:
        lora (LoRa): The LoRa object to configure.
    """
    lora.set_mode(MODE.SLEEP)
    lora.set_freq(LORA_PARAMS['freq'])
    lora.set_spreading_factor(LORA_PARAMS['spreading_factor'])
    lora.set_bw(LORA_PARAMS['bandwidth'])
    lora.set_coding_rate(LORA_PARAMS['coding_rate'])
    lora.set_preamble(LORA_PARAMS['preamble'])
    lora.set_implicit_header_mode(LORA_PARAMS['implicit_header'])
    lora.set_sync_word(LORA_PARAMS['sync_word'])
    lora.set_tx_power(LORA_PARAMS['tx_power'], LORA_PARAMS['power_mode'])
    lora.set_enable_crc(LORA_PARAMS['enable_CRC'])