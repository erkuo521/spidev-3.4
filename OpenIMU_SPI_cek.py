'''
OpenIMU SPI package version 26.0.13.
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
    bcm 27                nRST
@cek from Aceinna 2019.11.4
'''

import os
import sys
import spidev
import time, math
import struct
try:
    import RPi.GPIO as GPIO
except RuntimeError:
    print("Error import RPi.GPIO!")
import traceback
from gpio import *

class SpiOpenIMU:
    def __init__(self, target_module = "300", fw='0.0', cs_pin = 4, interrupt_pin = 17, drdy_status = False):
        '''
        pin number use the BCM code
        '''        

        self.spi = spidev.SpiDev()
        self.cs_channel = cs_pin
        self.interrupt_channel = interrupt_pin
        self.drdy = drdy_status
        self.speed = 1000000 # 1M
        self.delay = 0 #ns
        self.word = 8 #硬件限制为8位
        self.fw_version = fw

        self.power = aceinna_gpio(use_gpio=True)# bcm gpio rst EVK power

        

        self.gpio_setting()
        self.spidev_setting()
        self.check_settings()
        
        time.sleep(0.1)

        self.module = target_module
        print("initialize based on: %s, with DRDY_usage: %s" % (self.module, self.drdy))

    def gpio_setting(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.cs_channel,GPIO.OUT)
        GPIO.output(self.cs_channel,GPIO.HIGH) # used as CS line replace CS0 default in Pi3 board        

        if self.drdy:
            GPIO.setup(self.interrupt_channel,GPIO.IN) # channel used as IMU data ready detection
            time.sleep(0.4)
            GPIO.add_event_detect(self.interrupt_channel,GPIO.FALLING)            
        return True

    def single_read(self, target_register):
        # if self.drdy and self.module != "300":
        #     while not GPIO.event_detected(self.interrupt_channel):                
        #         pass 
        if self.module == "381":
            time.sleep(0.000010)
            GPIO.output(self.cs_channel,GPIO.LOW) 
            self.spi.xfer2([target_register,0x00],self.speed,self.speed)  #return data of 0000
            GPIO.output(self.cs_channel,GPIO.HIGH) 
            time.sleep(0.000010)
            GPIO.output(self.cs_channel,GPIO.LOW) 
            resp_single = self.spi.xfer2([0x00,0x00],self.speed,self.speed)  #receive the back target data
            GPIO.output(self.cs_channel,GPIO.HIGH)
            return self.combine_reg('>h', resp_single[0],resp_single[1])
        else:
            time.sleep(0.000010)
            GPIO.output(self.cs_channel,GPIO.LOW) 
            resp_single = self.spi.xfer2([target_register,0x00,0x00,0x00],self.speed,self.speed)         
            GPIO.output(self.cs_channel,GPIO.HIGH) 
            print("SPI raw read：", hex(resp_single[2]), hex(resp_single[3]))                  
            return self.combine_reg('>h', resp_single[2],resp_single[3])
        
    def single_write(self, target_register, target_data):
        # if self.drdy and self.module != "300":
        #     while not GPIO.event_detected(self.interrupt_channel):                
        #         pass 
        GPIO.output(self.cs_channel,GPIO.LOW)    
        temp_reg = target_register | 0x80       
        self.spi.xfer2([temp_reg, target_data],self.speed,self.speed)  #write data, such as 0xF010, target address is 0x70, and data input is 0x10
        GPIO.output(self.cs_channel,GPIO.HIGH)
        return True 
    
    def burst_read(self, first_register, subregister_num, sratm_fac):  
        '''
        sratm_fac={"rate":[0.005, 0], "accel":[0.25, 0]} 
        status, rate, accel, temp, mag factors dict
        '''         
        sts, rate, acc, deg, tmstp, temp, mag = [], [], [], [], [], [], []

        # if self.drdy and self.module != "300":  # 300 no drdy now, so only not 300 will go next
        #     while not GPIO.event_detected(self.interrupt_channel):                
        #         pass 
        while (not GPIO.event_detected(self.interrupt_channel)) and self.drdy:                
            pass 
        if "381" in self.module:
            GPIO.output(self.cs_channel,GPIO.LOW)
            resp = self.spi.xfer2([first_register,0x00],self.speed,self.speed)
            GPIO.output(self.cs_channel,GPIO.HIGH)
            for i_381 in range(subregister_num):
                time.sleep(0.000010)
                GPIO.output(self.cs_channel,GPIO.LOW)
                resp += self.spi.xfer2([0x00,0x00],self.speed,self.speed)[:]
                GPIO.output(self.cs_channel,GPIO.HIGH)
            #unit:degree per second
            rate.append(self.combine_reg('>h', resp[4],resp[5]) * (sratm_fac.get("rate")[0]) + (sratm_fac.get("rate")[1]))
            rate.append(self.combine_reg('>h', resp[6],resp[7]) * (sratm_fac.get("rate")[0]) + (sratm_fac.get("rate")[1]))
            rate.append(self.combine_reg('>h', resp[8],resp[9]) * (sratm_fac.get("rate")[0]) + (sratm_fac.get("rate")[1]))
            #unit:mg
            acc.append(self.combine_reg('>h', resp[10],resp[11]) * (sratm_fac.get("accel")[0]) + (sratm_fac.get("accel")[1]))
            acc.append(self.combine_reg('>h', resp[12],resp[13]) * (sratm_fac.get("accel")[0]) + (sratm_fac.get("accel")[1]))
            acc.append(self.combine_reg('>h', resp[14],resp[15]) * (sratm_fac.get("accel")[0]) + (sratm_fac.get("accel")[1]))
        else:     #300,330 is here                   
            GPIO.output(self.cs_channel,GPIO.LOW)
            # xfer2([value],speed_hz,delay_usec_cs), SPI bi-direction data transfer.
            # default 8 bits mode, if speed_hz set to zero means the maximun supported SPI clock.
            # delay_usec_cs is the cs hold delay
            first_register_send = [first_register,0x00]
            if '330BA' in self.module and first_register == 0x3D:
                subregister_num += 6
            for i_else in range(2*subregister_num):
                first_register_send.append(0x00)
            resp = self.spi.xfer2(first_register_send,self.speed,2*self.delay)
            GPIO.output(self.cs_channel,GPIO.HIGH)

            sts.append(self.combine_reg('>H', resp[2], resp[3]) * (sratm_fac.get("status")[0]) + (sratm_fac.get("status")[1]))
            #unit:degree per second
            if '330BA' in self.module and first_register == 0x3D:
                rate.append(self.combine_reg('>i', resp[4],resp[5],resp[6],resp[7]) * (sratm_fac.get("rate")[0]) + (sratm_fac.get("rate")[1]))
                rate.append(self.combine_reg('>i', resp[8],resp[9], resp[10],resp[11]) * (sratm_fac.get("rate")[0]) + (sratm_fac.get("rate")[1]))
                rate.append(self.combine_reg('>i', resp[12],resp[13], resp[14],resp[15]) * (sratm_fac.get("rate")[0]) + (sratm_fac.get("rate")[1]))
            else:                
                rate.append(self.combine_reg('>h', resp[4],resp[5]) * (sratm_fac.get("rate")[0]) + (sratm_fac.get("rate")[1]))
                rate.append(self.combine_reg('>h', resp[6],resp[7]) * (sratm_fac.get("rate")[0]) + (sratm_fac.get("rate")[1]))
                rate.append(self.combine_reg('>h', resp[8],resp[9]) * (sratm_fac.get("rate")[0]) + (sratm_fac.get("rate")[1]))
            #unit:g
            if '330BA' in self.module and first_register == 0x3D:
                acc.append(self.combine_reg('>i', resp[16],resp[17], resp[18],resp[19]) * (sratm_fac.get("accel")[0]) + (sratm_fac.get("accel")[1]))
                acc.append(self.combine_reg('>i', resp[20],resp[21], resp[22],resp[23]) * (sratm_fac.get("accel")[0]) + (sratm_fac.get("accel")[1]))
                acc.append(self.combine_reg('>i', resp[24],resp[25], resp[26],resp[27]) * (sratm_fac.get("accel")[0]) + (sratm_fac.get("accel")[1])) 
            else: 
                acc.append(self.combine_reg('>h', resp[10],resp[11]) * (sratm_fac.get("accel")[0]) + (sratm_fac.get("accel")[1]))
                acc.append(self.combine_reg('>h', resp[12],resp[13]) * (sratm_fac.get("accel")[0]) + (sratm_fac.get("accel")[1]))
                acc.append(self.combine_reg('>h', resp[14],resp[15]) * (sratm_fac.get("accel")[0]) + (sratm_fac.get("accel")[1])) 
            #unit:deg
            if '330BI' in self.module and first_register == 0x3F:
                deg.append(self.combine_reg('>h', resp[18],resp[19]) * 360/65536)
                deg.append(self.combine_reg('>h', resp[20],resp[21]) * 360/65536)
                deg.append(self.combine_reg('>h', resp[22],resp[23]) * 360/65536)
                # return rate, acc, deg 
            if '330BA' in self.module and first_register == 0x3D:
                temp.append(self.combine_reg('>h', resp[28],resp[29]) * (sratm_fac.get("temp")[0]) + (sratm_fac.get("temp")[1]))
            else:  
                temp.append(self.combine_reg('>h', resp[16],resp[17]) * (sratm_fac.get("temp")[0]) + (sratm_fac.get("temp")[1]))
            if ("330BA" in self.module or '331BI' in self.module) and (first_register == 0x3F or first_register == 0x3D):
                if first_register == 0x3F:
                    tmstp.append(self.combine_reg('>H', resp[18],resp[19]) * (sratm_fac.get("time")[0]) + (sratm_fac.get("time")[1]))
                    tmstp.append(self.combine_reg('>H', resp[20],resp[21]) * (sratm_fac.get("time")[0]) + (sratm_fac.get("time")[1]))
                else:
                    tmstp.append(self.combine_reg('>H', resp[30],resp[31]) * (sratm_fac.get("time")[0]) + (sratm_fac.get("time")[1]))
                    tmstp.append(self.combine_reg('>H', resp[32],resp[33]) * (sratm_fac.get("time")[0]) + (sratm_fac.get("time")[1]))
                # return rate, acc, tmstp               
            if '300ZI' in self.module and first_register == 0x3F:
                mag.append(self.combine_reg('>h', resp[18],resp[19]) * (sratm_fac.get("mag")[0]) + (sratm_fac.get("mag")[1]))
                mag.append(self.combine_reg('>h', resp[20],resp[21]) * (sratm_fac.get("mag")[0]) + (sratm_fac.get("mag")[1]))
                mag.append(self.combine_reg('>h', resp[22],resp[23]) * (sratm_fac.get("mag")[0]) + (sratm_fac.get("mag")[1])) 
            if '300ZI' in self.module and first_register == 0x3D:
                # deg.append(self.combine_reg('>h', resp[18],resp[19]) * 57.3 * (2*math.pi)/65536) #65536/(2*math.pi)=10430.378350470453   65536/360=0.0054931640625
                # deg.append(self.combine_reg('>h', resp[20],resp[21]) *  57.3 * (2*math.pi)/65536)
                # deg.append(self.combine_reg('>h', resp[22],resp[23]) *  57.3 * (2*math.pi)/65536)     
                deg.append(self.combine_reg('>h', resp[18],resp[19]) * (sratm_fac.get("vg_angle")[0]) + (sratm_fac.get("vg_angle")[1]))
                deg.append(self.combine_reg('>h', resp[20],resp[21]) * (sratm_fac.get("vg_angle")[0]) + (sratm_fac.get("vg_angle")[1]))
                deg.append(self.combine_reg('>h', resp[22],resp[23]) * (sratm_fac.get("vg_angle")[0]) + (sratm_fac.get("vg_angle")[1]))       
        return sts, rate, acc, temp, mag, deg, tmstp

    def spidev_setting(self):
        bus = 0    #supporyed values:0,1
        device = 1   #supported values:0,1   default: 0
        self.spi.open(bus,device)    #connect to the device. /dev/spidev<bus>.<device>
        self.spi.bits_per_word = self.word #默认是8，系统上
        self.spi.max_speed_hz = self.speed
        self.spi.mode = 0b11
        #spi.bits_per_word = 0
        #spi.cshigh #default CS0 in pi3 board
        #spi.lsbfirst = False
        #spi.threewire = 0
        return True

    def check_settings(self):
        print(self.spi.mode)
        print(self.spi.threewire)
        print(self.spi.cshigh)
        print(self.spi.bits_per_word)
        print(self.spi.lsbfirst)
        return True
    def combine_reg(self,fmt='>h',*msb_lsb):
        temp_bytes = b''
        for i in msb_lsb: 
            temp_bytes += struct.pack('B',i)
        return struct.unpack(fmt,temp_bytes)[0]   #MSB firstly

    def power_reset(self, delay=2):
        '''
        #special for IMU331, WAIT 1.25S at least
        '''
        self.power.power_off()
        time.sleep(delay)
        self.power.power_on()
        time.sleep(delay)


    def __del__(self):
        GPIO.cleanup()
        self.spi.close()
        
if __name__ == "__main__":       
    openimu_spi = SpiOpenIMU(target_module="330BI",drdy_status=True, fw='1.2.1')   #set the module name and drdy status(enalbe or not)-----------------step: 1
    burst_read, single_read, single_write = True, True, False  # set the read style, burst or single------------step:2
    f = open("data_" + str(openimu_spi.module) + ".txt", "w")
    str_config = "module style:{0}; drdy:{1};   burst read:{2}; single read:{3} \n".format(openimu_spi.module, openimu_spi.drdy, burst_read, single_read)
    print(str_config)
    f.write(str_config) 
    input("Power on IMU !!!!!!!!")
    time.sleep(2)  
    try:        
        if openimu_spi.drdy == False:  # when no drdy, default SPI ODR is 100HZ 
            time.sleep(0.01)
        # for i_wd in range(9,12):
        # for i_wd in [0x00, 0x03,0x04,0x05,0x06,0x30,0x40,0x50,0x60,0x0B, 0x0B]:
        # ori_list = [0x0000, 0x0009, 0x0023, 0x002A, 0x0041, 0x0048, 0x0062, 0x006B, 0x0085, 0x008C, 0x0092, 0x009B, 0x00C4, 0x00CD, 0x00D3, 
        #             0x00DA, 0x0111, 0x0118, 0x0124, 0x012D, 0x0150, 0x0159, 0x0165, 0x016C
        #             ]
        # ori_list = [0x0009, 0x016C]
        # for i_wd in ori_list:
        if single_read:
            read_name = [
                        "X_Rate", "Y_Rate", "Z_Rate", "X_Accel", "Y_Accel", "Z_Accel","X_Mag", "Y_Mag", "Z_Mag", "BOARD_TEMP", "RATE_TEMP", "DRDY_RATE", "ACCEL_LPF", "ACCEL_SCALE_FACTOR", "RATE_SCALE_FACTOR", 
                        "SN_1", "SN_2", "SN_3", "PRODUCT_ID", "MASTER_STATUS", "HW_STATUS", "SW_STATUS", "ACCEL_RANGE/RATE_RANGE", 
                        "ORIENTATION_MSB/ORIENTATION_LSB", "SAVE_CONFIG", "RATE_LPF", "HW_VERSION/SW_VERSION"
                        ]
            read_reg = [
                        0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E, 0x10, 0x12, 0x14, 0x16, 0x18, 0x37, 0x38, 0x46, 0x47, 
                        0x52, 0x54, 0x58, 0x56, 0x5A, 0x5C, 0x5E, 0x70, 0x74, 0x76, 0x78, 0x7E
                        ]  
            # read_name = ["ORIENTATION_MSB"]
            # read_reg = [0x74]
            for i in zip(read_name, read_reg):                
                read_value = openimu_spi.single_read(i[1])
                hex_value = hex(read_value)
                prt_list = [i[0], hex(i[1]), hex_value]
                print(prt_list)
                if 'Rate' in i[0]: 
                    read_value /= 64
                elif 'Accel' in i[0]:
                    read_value /= 4000
                elif 'Mag' in i[0]:
                    read_value /= 16354
                elif 'TEMP' in i[0]:
                    read_value = read_value*0.073111172849435 + 31.0
                str_temp = "{0:_<40s}0x{1:<5X} read value: 0d {2:<10} hex value: {3:<10s}\n".format(i[0], i[1], read_value, hex_value)
                print(str_temp)
                f.write(str(prt_list) + '\n' + str_temp) 
            
        if single_write:    
            while input('need write? y/n?') != 'y':
                pass                            
            write_name = ["packet rate", "Accel LPF", "orimsb", "orilsb", "Rate LPF", "save config"]
            write_reg = [0x37, 0x38, 0x74, 0x75, 0x78, 0x76]
            write_data = [0x01, 0x40, 0x00, 0x6B, 0x40, 0x00]
            # write_name = ["ORIENTATION_LSB"]
            # write_reg = [0x75]
            # write_data = [0x02]    
            # write_data = [i_wd, i_wd]            
            # write_data = [i_wd & 0xFF]
            for j in zip(write_name, write_reg, write_data):    #start to write registers
                print("write_name:{0:<40s}, write address:0x{1:<5X}, wirte data:0x{2:<5X}".format(j[0], j[1], j[2]))            
                openimu_spi.single_write(j[1], j[2])
                time.sleep(0.5)
        # if single_read or single_write:
        #     break 
        while input('need burst read? y/n?') != 'y':
            pass  
        while burst_read: # not seting the ODR, if you use burst read, it will same with frequency of DRDY            
            if ('330BI' in openimu_spi.module) or ('330BA' in openimu_spi.module):
                # list_rate, list_acc = openimu_spi.burst_read(first_register=0x3E,subregister_num=8)     #input the read register and numbers of subregisters want to read together
                # str_burst = "time:{0:>10f};  gyro:{1:>25s};  accel:{2:>25s} \n".format(
                #     time.clock(), ", ".join([str(x) for x in list_rate]), ", ".join([str(x) for x in list_acc])
                #     )
                list_sts, list_rate, list_acc, list_temp, list_mag, list_deg, tmstamp = openimu_spi.burst_read(first_register=0x3E,subregister_num=8)     #input the read register and numbers of subregisters want to read together
                str_burst = "time:{0:>10f};  gyro:{1:>50s};  accel:{2:>50s}; timestamp:{3:>25s} \n".format(
                    time.clock(), ", ".join([str(x) for x in list_rate]), ", ".join([str(x) for x in list_acc]), ", ".join([str(x) for x in tmstamp])
                )
                
            else:
                list_sts, list_rate, list_acc, list_temp, list_mag, list_deg, tmstamp= openimu_spi.burst_read(first_register=0x3D,subregister_num=11)
                str_burst = "time:{0:>20f};  status:{3:>20s} ; gyro:{1:>50s};  accel:{2:>40s}; temp:{4:>10s}; mag:{5:>20s}; deg:{6:>20s}\n".format(
                    time.clock(), ", ".join([str(x) for x in list_rate]), ", ".join([str(x) for x in list_acc]), ", ".join([str(x) for x in list_sts]), 
                    ", ".join([str(x) for x in list_temp]), ", ".join([str(x) for x in list_mag]), ", ".join([str(x) for x in list_deg])
                    )
            print(str_burst)               
            f.write(str_burst)
            # input('next cycle')
    except KeyboardInterrupt:
        f.close()
        print("stoped by customer!")
    
    # except Exception as e:
    #     print(e)
    #     traceback.print_exc()
        




















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


