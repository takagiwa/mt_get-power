#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import serial
import time
import binascii
import os

rbid = "00000000000000000000000000000000"
rbpwd = "XXXXXXXXXXXX"
scanDuration = 4
retryLimit = 14 # up to 14
measureInterval = 60 # in sec
showResponse = True

serialPortDev = '/dev/ttyUSB0'
ser = serial.Serial(serialPortDev, 115200)

# Version
if showResponse:
  print("==== VERSION ====")
ser.write(str.encode("SKVER\r\n"))
if showResponse:
  print( ser.readline().strip().decode('utf-8') ) # echo back
else:
  ser.readline()
line = ser.readline().strip().decode('utf-8')
if line.startswith("FAIL"):
  if showResponse:
    print(line)
    print("[ERROR] Something wrong.")
    sys.exit()
if showResponse:
  print( line )
if showResponse:
  print( ser.readline().strip().decode('utf-8') ) # ok
else:
  ser.readline()

# Auth
ser.write(str.encode("SKSETPWD C " + rbpwd + "\r\n"))
if showResponse :
  print("==== AUTH ====")
  print( ser.readline().strip().decode('utf-8') ) # echo back
  print( ser.readline().strip().decode('utf-8') ) # ok
else :
  ser.readline()
  ser.readline()

ser.write(str.encode("SKSETRBID " + rbid + "\r\n"))
if showResponse :
  print( ser.readline().strip().decode('utf-8') ) # echo back
  print( ser.readline().strip().decode('utf-8') ) # ok
else :
  ser.readline()
  ser.readline()

if showResponse :
  print("==== SCAN ====")
scanRes = {}
while not "Channel" in scanRes :
  ser.write(str.encode("SKSCAN 2 FFFFFFFF " + str(scanDuration) + "\r\n"))

  scanEnd = False
  while not scanEnd :
    line = ser.readline().decode('utf-8')
    if showResponse:
      print(line, end="")

    if line.startswith("EVENT 22") :
      scanEnd = True
    elif line.startswith("  ") :
      cols = line.strip().split(':')
      scanRes[cols[0]] = cols[1]
  scanDuration += 1

  if retryLimit < scanDuration and not "Channel" in scanRes :
    print("[ERROR] Scan retry over")
    sys.exit()

ser.write(str.encode("SKSREG S2 " + scanRes["Channel"] + "\r\n"))
if showResponse :
  print("==== SET CHANNEL ====")
  print( ser.readline().strip().decode('utf-8') ) # echo back
  print( ser.readline().strip().decode('utf-8') ) # ok
else :
  ser.readline()
  ser.readline()

ser.write(str.encode("SKSREG S3 " + scanRes["Pan ID"] + "\r\n"))
if showResponse :
  print("==== SET PAN ID ====")
  print( ser.readline().strip().decode('utf-8') ) # echo back
  print( ser.readline().strip().decode('utf-8') ) # ok
else :
  ser.readline()
  ser.readline()

ser.write(str.encode("SKLL64 " + scanRes["Addr"] + "\r\n"))
if showResponse :
  print("==== IPv6 ADDR ====")
  print( ser.readline().strip().decode('utf-8') ) # echo back
else :
  ser.readline()
ipv6Addr = ser.readline().strip().decode('utf-8')
if showResponse :
  print(ipv6Addr)

ser.write(str.encode("SKJOIN " + ipv6Addr + "\r\n"))
if showResponse :
  print("==== START CONNECT ====")
  print( ser.readline().strip().decode('utf-8') ) # echo back
  print( ser.readline().strip().decode('utf-8') ) # ok
else :
  ser.readline()
  ser.readline()

bConnected = False
while not bConnected :
  line = ser.readline().decode('utf-8')
  if showResponse :
    print(line, end="")
  if line.startswith("EVENT 24") :
    print("[ERROR] Failed to connect.")
    sys.exit()
  elif line.startswith("EVENT 25") :
    bConnected = True

ser.timeout = 2

if showResponse :
  print("==== INSTANCE LIST ====")
  print( ser.readline().strip().decode('utf-8') ) # instance list
  print( ser.readline().strip().decode('utf-8') ) # add
else :
  ser.readline()
  ser.readline()


while True :
    echonetLiteFrame = ""
    echonetLiteFrame += "\x10\x81"
    echonetLiteFrame += "\x00\x01"
    echonetLiteFrame += "\x05\xFF\x01"
    echonetLiteFrame += "\x02\x88\x01"
    echonetLiteFrame += "\x62"
    echonetLiteFrame += "\x03"
    echonetLiteFrame += "\xE1"
    echonetLiteFrame += "\x00"
    echonetLiteFrame += "\xE0"
    echonetLiteFrame += "\x00"
    echonetLiteFrame += "\xD7"
    echonetLiteFrame += "\x00"
    command = "SKSENDTO 1 {0} 0E1A 1 {1:04X} ".format(ipv6Addr, len(echonetLiteFrame))
    ser.write(str.encode(command)+b'\x10\x81\x00\x01\x05\xFF\x01\x02\x88\x01\x62\x03\xD7\x00\xE1\x00\xE0\x00')

    if showResponse :
      print( ser.readline().strip().decode('utf-8') ) # echo back
      print( ser.readline().strip().decode('utf-8') ) # EVENT 21
      print( ser.readline().strip().decode('utf-8') ) # ok
    else :
      ser.readline()
      ser.readline()
      ser.readline()
    line = ser.readline()
    if showResponse :
      print( line.strip().decode('utf-8') )

    if line.decode('utf-8').startswith("ERXUDP") :
      cols = line.strip().decode('utf-8').split(' ')
      res = cols[8]

      # https://www.meti.go.jp/committee/kenkyukai/shoujo/smart_house/pdf/009_s03_00.pdf
      # page 35

      tid = res[4:4+4]
      seoj = res[8:8+6]
      deoj = res[14:14+6]
      ESV = res[20:20+2]
      OPC = res[22:22+2]
      if showResponse:
        print("TID: {0} / SEOJ: {1} / DEOJ: {2} / ESV: {3} / OPC: {4}".format(tid, seoj, deoj, ESV, OPC))
      if seoj == "028801" and ESV == "72" :
        #EPC = res[24:24+2]
        #if EPC == "82" :
        #  hexData = line[-4:]
        #  print("EPC: 0x82 / Data: {0}".format(hexData))
        #elif EPC == "88" :
        #  hexData = line[-1:]
        #  print("EPC: 0x88 / Data: {0}".format(hexData))
        #elif EPC == "8A" :
        #  hexData = line[-3:]
        #  print("EPC: 0x8A / Data: {0}".format(hexData))
        #elif EPC == "80" :
        #  hexData = line[-1:]
        #  print("EPC: 0x80 / Data: {0}".format(hexdata))
        #elif EPC == "D3" :
        #  hexData = line[-4:]
        #  print("EPC: 0xD3 / Data: {0}".format(hexData))
        #elif EPC == "D7" :
        #  hexData = line[-1:]
        #  print("EPC: 0xD7 / Data: {0}".format(hexData))
        #elif EPC == "E0" :
        #  hexData = line[-8:]
        #  print("EPC: 0xE0 / Data: {0}".format(hexData))
        #elif EPC == "E1" :
        #  hexData = line[-8:]
        #  print("EPC: 0xE1 / Data: {0}".format(hexData))
        #elif EPC == "E7" :
        #  hexPower = line[-8:]
        #  intPower = int(hexPower, 16)
        #  print("Power:{0}[W]".format(intPower))

        # D7
        epc1 = res[24:24+2]
        pdc1 = res[26:26+2]
        edt1 = res[28:28+2]
        sigdigit = int(edt1, 16)
        if showResponse:
          print("{0} / {1} / {2}".format(epc1, pdc1, edt1))
          print("sigdigit: {0}".format(sigdigit))
        # E1
        epc2 = res[30:30+2]
        pdc2 = res[32:32+2]
        edt2 = res[34:34+2]
        unitnum = 1;
        if edt2 == "00":
          unitnum = 1.0
        elif edt2 == "01":
          unitnum = 0.1
        elif edt2 == "02":
          unitnum = 0.01
        elif edt2 == "03":
          unitnum = 0.001
        elif edt2 == "04":
          unitnum = 0.0001
        elif edt2 == "0A":
          unitnum = 10.0
        elif edt2 == "0B":
          unitnum = 100.0
        elif edt2 == "0C":
          unitnum = 1000.0
        elif edt2 == "0D":
          unitnum = 10000.0
        if showResponse:
          print("{0} / {1} / {2}".format(epc2, pdc2, edt2))
        # E0
        epc3 = res[36:36+2]
        pdc3 = res[38:38+2]
        edt3 = res[40:40+8]
        pow_base = int(edt3, 16)
        if showResponse:
          print("{0} / {1} / {2}".format(epc3, pdc3, edt3))
        f_power = pow_base * unitnum
        i_power = int(f_power * 1000)
        if showResponse:
          print("power: {0} [kW]".format(f_power))
        if True:
          # make & write
          fn = '/tmp.bak/power.new'
          f = open(fn, 'w')
          #s = '%f\n' % f_power
          s = '%d\n' % i_power
          f.write(s)
          f.flush()
          os.fsync(f.fileno())
          f.close

          # move new & old
          mv = ''
          fn = '/tmp.bak/power'
          if os.path.exists(fn):
            mv = 'mv /tmp.bak/power /tmp.bak/power.bak &&'
          cmd = '%s mv /tmp.bak/power.new /tmp.bak/power' % mv
          os.system(cmd)

      time.sleep(measureInterval)

      if True:
        # remove previous
        fn = '/tmp.bak/power.bak'
        if os.path.exists(fn):
          os.remove(fn)

ser.close()
