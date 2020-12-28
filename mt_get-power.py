#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import serial
import time
import binascii
import os
import logging

# Bルート認証ID（東京電力パワーグリッドから郵送で送られてくるヤツ）
rbid = "00000000000000000000000000000000"
# Bルート認証パスワード（東京電力パワーグリッドからメールで送られてくるヤツ）
rbpwd = "XXXXXXXXXXXX"
scanDuration = 4   # スキャン時間。サンプルでは6なんだけど、4でも行けるので。（ダメなら増やして再試行）
retryLimit = 14 # up to 14
measureInterval = 60 # in sec
showResponse = True
valueFileName = '/tmp/power'
waitBase = 5*60
waitInc = 3*60
breakLimit = 5

logging.basicConfig(level=logging.INFO)
waitAfterFailure = waitBase
breakCount = 0

# シリアルポートデバイス名
serialPortDev = '/dev/ttyUSB0'  # Linux(ラズパイなど）の場合
#serialPortDev = '/dev/cu.usbserial-A103BTPR'    # Mac の場合

while True:

  # シリアルポート初期化
  ser = serial.Serial(serialPortDev, 115200)

  while True:

    # Version
    logging.info("==== VERSION ====")
    ser.write(str.encode("SKVER\r\n"))
    ser.flush()
    time.sleep(1)
    logging.info(ser.read_until().strip().decode('utf-8')) # echo back
    line = ser.read_until().strip().decode('utf-8')
    if line.startswith("FAIL"):
      logging.error(line)
      logging.error("[ERROR] Something wrong.")
      #sys.exit()
      if (breakCount >= breakLimit):
        break;
      time.sleep(waitAfterFailure)
      waitAfterFailure += waitInc
      breakCount += 1
      continue
    logging.info(line)
    logging.info(ser.read_until().strip().decode('utf-8')) # ok
    line = ''

    waitAfterFailure = waitBase
    breakCount = 0

    # Bルート認証パスワード設定
    logging.info("==== AUTH ====")
    ser.write(str.encode("SKSETPWD C " + rbpwd + "\r\n"))
    ser.flush()
    time.sleep(1)
    logging.info(ser.read_until().strip().decode('utf-8')) # echo back
    logging.info(ser.read_until().strip().decode('utf-8')) # ok

    # Bルート認証ID設定
    ser.write(str.encode("SKSETRBID " + rbid + "\r\n"))
    ser.flush()
    time.sleep(1)
    logging.info(ser.read_until().strip().decode('utf-8')) # echo back
    logging.info(ser.read_until().strip().decode('utf-8')) # ok

    logging.info("==== SCAN ====")
    scanRes = {} # スキャン結果の入れ物
    while not "Channel" in scanRes :
      line = ''
      # アクティブスキャン（IE あり）を行う
      # 時間かかります。10秒ぐらい？
      ser.write(str.encode("SKSCAN 2 FFFFFFFF " + str(scanDuration) + "\r\n"))
      ser.flush()
      time.sleep(1)

      # スキャン1回について、スキャン終了までのループ
      scanEnd = False
      while not scanEnd :
        line = ser.read_until().decode('utf-8')
        logging.info(line)

        if line.startswith("EVENT 22") :
          # スキャン終わったよ（見つかったかどうかは関係なく）
          scanEnd = True
        elif line.startswith("  ") :
          # スキャンして見つかったらスペース2個あけてデータがやってくる
          cols = line.strip().split(':')
          scanRes[cols[0]] = cols[1]
        elif line.startswith("FAIL") :
          time.sleep(waitAfterFailure)
          waitAfterFailure += waitInc
          breakCount += 1
          break

      if breakCount > 0:
        break;

      scanDuration += 1

      if retryLimit < scanDuration and not "Channel" in scanRes :
        # 引数としては14まで指定できるが、7で失敗したらそれ以上は無駄っぽい
        logging.error("[ERROR] Scan retry over")
        sys.exit() #### 終了 ####

    if breakCount >= breakLimit:
      logging.warning("[WARNING] Scan retry over")
      break
    if breakCount > 0:
      continue

    line = ''
    waitAfterFailure = waitBase
    breakCount = 0

    # スキャン結果からChannelを設定。
    logging.info("==== SET CHANNEL ====")
    ser.write(str.encode("SKSREG S2 " + scanRes["Channel"] + "\r\n"))
    ser.flush()
    time.sleep(1)
    logging.info(ser.read_until().strip().decode('utf-8')) # echo back
    logging.info(ser.read_until().strip().decode('utf-8')) # ok

    # スキャン結果からPan IDを設定
    logging.info("==== SET PAN ID ====")
    ser.write(str.encode("SKSREG S3 " + scanRes["Pan ID"] + "\r\n"))
    ser.flush()
    time.sleep(1)
    logging.info(ser.read_until().strip().decode('utf-8')) # echo back
    logging.info(ser.read_until().strip().decode('utf-8')) # ok

    # MACアドレス(64bit)をIPV6リンクローカルアドレスに変換。
    # (BP35A1の機能を使って変換しているけど、単に文字列変換すればいいのではという話も？？)
    logging.info("==== IPv6 ADDR ====")
    ser.write(str.encode("SKLL64 " + scanRes["Addr"] + "\r\n"))
    ser.flush()
    time.sleep(1)
    logging.info(ser.read_until().strip().decode('utf-8')) # echo back
    ipv6Addr = ser.read_until().strip().decode('utf-8')
    logging.info(ipv6Addr)

    # PANA 接続シーケンスを開始します。
    logging.info("==== START CONNECT ====")
    ser.write(str.encode("SKJOIN " + ipv6Addr + "\r\n"))
    ser.flush()
    time.sleep(1)
    logging.info(ser.read_until().strip().decode('utf-8')) # echo back
    logging.info(ser.read_until().strip().decode('utf-8')) # ok

    # PANA 接続完了待ち（10行ぐらいなんか返してくる）
    bConnected = False
    while not bConnected :
      line = ser.read_until().decode('utf-8')
      logging.info(line)
      if line.startswith("EVENT 24") :
        logging.error("[ERROR] Failed to connect.")
        #sys.exit() #### 終了 ####
        if breakCount >= breakLimit:
          break
        time.sleep(waitAfterFailure)
        waitAfterFailure += waitInc
        breakCount += 1
        continue
      elif line.startswith("EVENT 25") :
        # 接続完了！
        bConnected = True

    if breakCount >= breakLimit:
      logging.warning("[WARNING] Connection retry over")
      break

    # これ以降、シリアル通信のタイムアウトを設定
    ser.timeout = 2

    waitAfterFailure = waitBase
    breakCount = 0

    # スマートメーターがインスタンスリスト通知を投げてくる
    # (ECHONET-Lite_Ver.1.12_02.pdf p.4-16)
    logging.info("==== INSTANCE LIST ====")
    logging.info(ser.read_until().strip().decode('utf-8')) # instance list
    logging.info(ser.read_until().strip().decode('utf-8')) # add

    while True :

      # 改造箇所
      # 二つのデータをリクエストしている。
      # もうちょっとスマートにしよう。
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
      # コマンド送信
      ser.write(str.encode(command)+b'\x10\x81\x00\x01\x05\xFF\x01\x02\x88\x01\x62\x03\xD7\x00\xE1\x00\xE0\x00')
      ser.flush()
      time.sleep(1)

      # 失敗したときの例
      # SKSENDTO ...
      # EVENT 21 ...
      # OK
      # S
      # FAIL ER09
      # ERXUDP ...
      # (大量の空行)

      l_echo = ser.read_until().strip().decode('utf-8') # echo
      l_event = ser.read_until().strip().decode('utf-8') # event 21
      l_ok = ser.read_until().strip().decode('utf-8') # ok
      line = ''
      line = ser.read_until() # ERXUDPが来るはず
      logging.info(l_echo)
      logging.info(l_event)
      logging.info(l_ok)
      logging.info(line.strip().decode('utf-8'))
      e = 0;
      if not "SKSENDTO" in l_echo:
        e += 1
      if not "EVENT" in l_event:
        e += 1
      if not "OK" in l_ok:
        e += 1
      if e > 0:
        logging.error("Something wrong")
        logging.error(ser.read_until().strip().decode('utf-8'))
        logging.error(ser.read_until().strip().decode('utf-8'))
        logging.error(ser.read_until().strip().decode('utf-8'))
        logging.error("-")
        if breakCount >= breakLimit:
          break
        time.sleep(waitAfterFailure)
        waitAfterFailure += waitInc
        breakCount += 1
        break;

      # 受信データはたまに違うデータが来たり、
      # 取りこぼしたりして変なデータを拾うことがあるので
      # チェックを厳しめにしてます。
      if line.decode('utf-8').startswith("ERXUDP") :
        cols = line.strip().decode('utf-8').split(' ')
        if len(cols) < 9:
          time.sleep(3)
          break
        res = cols[8]
        if len(res) < 48: # 49?
          time.sleep(3)
          break

        # https://www.meti.go.jp/committee/kenkyukai/shoujo/smart_house/pdf/009_s03_00.pdf
        # page 35

        tid = res[4:4+4]
        seoj = res[8:8+6]
        deoj = res[14:14+6]
        ESV = res[20:20+2]
        OPC = res[22:22+2]
        #if showResponse:
        #  print("TID: {0} / SEOJ: {1} / DEOJ: {2} / ESV: {3} / OPC: {4}".format(tid, seoj, deoj, ESV, OPC))
        logging.info("TID: {0} / SEOJ: {1} / DEOJ: {2} / ESV: {3} / OPC: {4}".format(tid, seoj, deoj, ESV, OPC))
        if seoj == "028801" and ESV == "72" :

          # D7 = 有効桁数
          epc1 = res[24:24+2]
          pdc1 = res[26:26+2]
          edt1 = res[28:28+2]
          sigdigit = int(edt1, 16)
          #if showResponse:
          #  print("{0} / {1} / {2}".format(epc1, pdc1, edt1))
          #  print("sigdigit: {0}".format(sigdigit))
          logging.info("{0} / {1} / {2}".format(epc1, pdc1, edt1))
          logging.info("sigdigit: {0}".format(sigdigit))

          # E1 = 単位
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
          #if showResponse:
          #  print("{0} / {1} / {2}".format(epc2, pdc2, edt2))
          logging.info("{0} / {1} / {2}".format(epc2, pdc2, edt2))

          # E0 = 積算電力
          epc3 = res[36:36+2]
          pdc3 = res[38:38+2]
          edt3 = res[40:40+8]
          pow_base = int(edt3, 16)
          #if showResponse:
          #  print("{0} / {1} / {2}".format(epc3, pdc3, edt3))
          logging.info("{0} / {1} / {2}".format(epc3, pdc3, edt3))

          # 積算電力をW単位で。小数点が入ると
          # munin のグラフの type の COUNTER や DERIVE がエラーになる。
          f_power = pow_base * unitnum
          i_power = int(f_power * 1000)
          #if showResponse:
          #  print("power: {0} [kW]".format(f_power))
          logging.info("power: {0} [kW]".format(f_power))
          if True:
            # 新しいファイルを作成し・・・
            fn = valueFileName + '.new'
            f = open(fn, 'w')
            s = '%d\n' % i_power
            f.write(s)
            f.flush()
            os.fsync(f.fileno())
            f.close

            # 前のファイルの .bak へのリネームと
            # 新しいファイルの無印へのリネームを
            # 一気に実行
            mv = ''
            fn = valueFileName
            if os.path.exists(fn):
              mv = 'mv ' + valueFileName + ' ' + valueFileName + '.bak &&'
            cmd = '%s mv ' % mv
            cmd += valueFileName + '.new ' + valueFileName
            os.system(cmd)

        time.sleep(measureInterval)

        if True:
          # 前のファイルを削除
          fn = valueFileName + '.bak'
          if os.path.exists(fn):
            os.remove(fn)

        waitAfterFailure = waitBase

      ser.reset_input_buffer()

    ser.reset_input_buffer()

    if breakCount >= breakLimit:
      break

  ser.close()
  logging.warning("[WARNING] Disconnect serial port for retry")
  time.sleep(waitAfterFailure)
