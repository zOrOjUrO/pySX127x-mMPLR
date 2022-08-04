#!/usr/bin/env python3

""" This program sends a response whenever it receives the "CNT" """

# Copyright 2022 zOrOjUrO.
#
# This file is part of pySX127x-mMPLR, a fork of rpsreal/pySX127xw which is fork of mayeranalytics/pySX127x.
#
# pySX127x is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public
# License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# pySX127x is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You can be released from the requirements of the license by obtaining a commercial license. Such a license is
# mandatory as soon as you develop commercial activities involving pySX127x without disclosing the source code of your
# own applications, or shipping pySX127x with a closed source product.
#
# You should have received a copy of the GNU General Public License along with pySX127.  If not, see
# <http://www.gnu.org/licenses/>.

import time
from SX127x.LoRa import *
#from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config import BOARD

from mMPLR.mMPLR import mMPLR

BOARD.setup()
BOARD.reset()
#parser = LoRaArgumentParser("Lora tester")


class mMPLRLoraClient(LoRa):
    def __init__(self, verbose=False):
        super(mMPLRLoraClient, self).__init__(verbose)
        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0] * 6)

        self.mplr = mMPLR(devId=1)

        self.corrupt = []
        self.nBatches = 0

    def sendData(self, raw):
        data = [int(hex(c), 0) for c in raw]
        self.write_payload(data)
        BOARD.led_on()
        self.set_mode(MODE.TX)
        time.sleep(2)

    def on_rx_done(self):
        BOARD.led_on()
        #print("\nRxDone")
        self.clear_irq_flags(RxDone=1)
        p = self.read_payload(nocheck=True)
        print(p)
        pkt = bytes(p)
        #print(packet) # Receive DATA
        BOARD.led_off()

        packet = self.mplr.parsePacket(rawpacket=pkt)
        header = packet.get("Header")
        flag = header.get("Flag")
        if flag == 0:
            print("\nSYN Received")
            self.destId = header.get("DeviceUID")
            #Generate Data for Transmission
            self.packets = self.mplr.getPackets(data="This is a Test", 
                                                dataType="0", 
                                                destinationId=self.destId)
            synack = self.mplr.genFlagPacket(DestinationID=self.destId,
                                            Service=0,
                                            BatchSize=self.mplr.BatchSize,
                                            Flag=1)
            time.sleep(3) # Wait for the client be ready
            print ("Send: SYN-ACK")
            self.state = 1
            self.sendData(synack)
            self.set_mode(MODE.SLEEP)
            self.reset_ptr_rx()
            self.set_mode(MODE.RXCONT)
            time.sleep(2)
        
        elif flag==5:
            print("\nReceived ACK")
            if self.state == 1:
                #sending data
                #for _ in range(2):
                self.sendData(self.packets[0])
                time.sleep(2)
                fin = self.mplr.genFlagPacket(DestinationID=self.destId,
                                                Service=0,
                                                BatchSize=self.mplr.BatchSize,
                                                Flag=4)
                self.sendData(fin)
                self.state = 5
                self.set_mode(MODE.SLEEP)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)
                time.sleep(2)

            elif self.state == 5:
                print("\nConnnection Terminated")
                self.state = 0
                time.sleep(5)
                self.reset_ptr_rx()
                self.set_mode(MODE.RXCONT)

            """    
            if req=="CNT":
                print("Received data request CNT")
                time.sleep(2)
                packets = self.mplr.getPackets("cz3gm8ix0gr092bnzyijsdmau4e8ublxb4gz2jx85gqir8r3sj5ekdigk139g6jalbe0xl1hro9xlvq2sewa8iqo9e46ap2eyu0coojtpfi6tzzre94719c17id9hpvhkw6amcvtmfdf1m9811o71xyx1yb3p9hx8hwcbo7f7qawlupgkm8kttbxqcbj0z53wotey1v33utg0lcjkbug4vx0jvunyxxfhbw0vjqaq493yyw5vsym6xcmkwy2z21ob9xgutg51n86nc9onrw8sgwp1v79bvl3pqo99bnlpsyorb4w1sct1cphr96qc7l6qi9v0u7dgvqiaq9w5ei9t3pvxqjux1dqhx23ffgdo1ke2ub9x4dpr2ioslyr8p2fyvwm30kpun5mok8deld43wmihc3c0ldg8yb01eu4xzdoc6fsmxsqs2poqa87ghdvxfqt24licn9hiureey069n3xdfsr7no8d21z5ndy45k1p6ndhxed", 1, 2)
                print("Sending ", self.mplr.BatchSize, " Packets")
                for packet in packets: 
                    print("Sending Packet --> ", packet)
                    self.sendData(packet)
            """    
        else:
            time.sleep(5)
            self.reset_ptr_rx()
            self.set_mode(MODE.RXCONT)

    def on_tx_done(self):
        print("\nTxDone")
        print(self.get_irq_flags())

    def on_cad_done(self):
        print("\non_CadDone")
        print(self.get_irq_flags())

    def on_rx_timeout(self):
        print("\non_RxTimeout")
        print(self.get_irq_flags())

    def on_valid_header(self):
        print("\non_ValidHeader")
        print(self.get_irq_flags())

    def on_payload_crc_error(self):
        print("\non_PayloadCrcError")
        print(self.get_irq_flags())

    def on_fhss_change_channel(self):
        print("\non_FhssChangeChannel")
        print(self.get_irq_flags())

    def start(self):          
        while True:
            self.reset_ptr_rx()
            self.set_mode(MODE.RXCONT) # Receiver mode
            while True:
                pass;
            

lora = mMPLRLoraClient(verbose=False)
#args = parser.parse_args(lora) # configs in LoRaArgumentParser.py

#     Slow+long range  Bw = 125 kHz, Cr = 4/8, Sf = 4096chips/symbol, CRC on. 13 dBm
lora.set_pa_config(pa_select=1, max_power=21, output_power=15)
lora.set_bw(BW.BW125)
lora.set_coding_rate(CODING_RATE.CR4_8)
lora.set_spreading_factor(12)
lora.set_rx_crc(True)
#lora.set_lna_gain(GAIN.G1)
#lora.set_implicit_header_mode(False)
lora.set_low_data_rate_optim(True)

#  Medium Range  Defaults after init are 434.0MHz, Bw = 125 kHz, Cr = 4/5, Sf = 128chips/symbol, CRC on 13 dBm
#lora.set_pa_config(pa_select=1)



assert(lora.get_agc_auto_on() == 1)

try:
    print("START")
    lora.start()
except KeyboardInterrupt:
    sys.stdout.flush()
    print("Exit")
    sys.stderr.write("KeyboardInterrupt\n")
finally:
    sys.stdout.flush()
    print("Exit")
    lora.set_mode(MODE.SLEEP)
BOARD.teardown()
