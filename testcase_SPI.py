'''
OpenIMU SPI package version 0.2.0.
-pip install spidev3.4, 
-read package through SPI interface, OpenIMU330BI test on Pi3 board(Raspbian OS,Raspberry 3B+).
-Spi slave: OpenIMU 330 EVK
-Pins connection:
    Pi3                   330/300 evk
	miso        <==>      miso
	mosi        <==>      mosi
	sck         <==>      sck
	gpio(bcm4)  <==>      cs   black line
    gpio(bcm17) <==>      drdy red line
	gnd         <==>      gnd
@cek from Aceinna 2019.11.4
'''

import os
import sys
from typing import Sequence
import spidev
import time, math
import struct
try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("Error import RPi.GPIO!")
from OpenIMU_SPI_cek import *

# f = open("test_case_" + str(openimu_spi.module) + ".txt", "w")
# str_config = "module style:{0}; drdy:{1};   burst read:{2}; single read:{3} \n".format(openimu_spi.module, openimu_spi.drdy, burst_read, single_read)
# print(str_config)
# f.write(str_config) 
 
class test_case:
    def __init__(self, spi_module, spi_config, recoredfile):
        '''
        pin number use the BCM code
        ''' 
        self.dev = spi_module
        self.config = spi_config
        self.file = recoredfile #add \n in end of str to keep enter
        self.sequence = self.config.get("set_register_sequence") #sequence of set_registers(0x37) 2 bytes feedback, 0--low address first(0x37--0x38), 1--high address first(0x38--0x37)

    def default_setting_check(self):
        registers = self.config.get("set_register")
        for i,j in zip(registers.keys(), registers.values()): 
            #j[0]--target register, j[1]--target data. if j[1]== None, igore
            if j[1] == "None":
                continue
            fb = self.dev.single_read(int(j[0],16))
            fb = (fb >> 8) & 0x00ff if self.sequence == 0 else (fb & 0xff00) >> 8
            rlt = 'pass' if fb == int(j[1], 16) else 'fail'
            pr = f"{i}-regist-{j[0]}-expect-{j[1]}-feedback-{hex(fb)}-result-{rlt}; \n"
            print(pr)
            self.file.write(pr) 
    
    def single_data_reading(self):
        registers = self.config.get("data_register")
        for i,j in zip(registers.keys(), registers.values()): 
        #j[0]--target register, j[1]--target data. if j[1]== None, igore
            fb = self.dev.single_read(int(j[0],16))
            fb_processed = fb * j[1] + j[2]
            # rlt = 'pass' if fb == int(j[1], 16) else 'fail'
            pr = f"{i}-regist-{j[0]}-feedback-{fb_processed}; \n"
            print(pr)
            self.file.write(pr) 




        




















    # polling mode reading spi interface, with drdy pin detection
    # try:
    #     while True:
    #         # GPIO.output(cs_channel,GPIO.LOW)
    #         # product_id = spi.xfer2([0x56,0x00,0x00,0x00],0,10)
    #         # GPIO.output(cs_channel,GPIO.HIGH)                     
    #         # print('id',product_id)            
    #         time.sleep(0.1)
            
    #         # if GPIO.event_detected(interrupt_channel):
    #         if True:
    #             time.sleep(0.5)
    #             GPIO.output(cs_channel,GPIO.LOW)
    #             # xfer2([value],speed_hz,delay_usec_cs), SPI bi-direction data transfer.
    #             # default 8 bits mode, if speed_hz set to zero means the maximun supported SPI clock.
    #             # delay_usec_cs is the cs hold delay
    #             resp = spi.xfer2([openimu_spi.burst_cmd_std,0x00,0x00,0x00,0x00,0x00,0x00,
    #                     0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00],0,10)
    #             GPIO.output(cs_channel,GPIO.HIGH)
    #             #unit:degree per second
    #             x_rate = openimu_spi.combine_reg(resp[4],resp[5])/200
    #             y_rate = openimu_spi.combine_reg(resp[6],resp[7])/200
    #             z_rate = openimu_spi.combine_reg(resp[8],resp[8])/200
    #             #unit:mg
    #             x_acc = openimu_spi.combine_reg(resp[10],resp[11])/4
    #             y_acc = openimu_spi.combine_reg(resp[12],resp[13])/4
    #             z_acc = openimu_spi.combine_reg(resp[14],resp[15])/4
    #             print('g/a',x_rate,y_rate,z_rate,x_acc,y_acc,z_acc)
            
            
            
    # #write to register
    # time.sleep(0.5)
    # GPIO.output(cs_channel,GPIO.LOW)             
    # resp1 = spi.xfer2([0x80|0x50,0x23],0,10)
    # time.sleep(0.5)
    # GPIO.output(cs_channel,GPIO.HIGH) 

    # 0x56 OPEN300 ID: 0x30(48) 0x00(0) 
    # 0x56 OPEN330 ID: 0x33(48) 0x00(0)
    # 0x56 IMU381 ID:  0X38(56) 0x10(16)  


