# mt_get-power

This software is to get data from Japanese smart meter.

スマートメーターから積算電力を取得して、その結果をテキストファイルで更新するプログラム。テキストファイルは主に、munin で使用する。

以下のサイトのコードをベースにしています。

- [スマートメーターのBルート接続で自宅電力消費量をMuninしてみた ── RL7023 Stick-D/IPSレビュー](http://blog.andromeda.jp/archives/2194)
- [RaspberryPiでスマートメータの電力を取得する](https://qiita.com/puma_46/items/1d1589583a0c6bef796c)
- [スマートメーターの情報を最安ハードウェアで引っこ抜く](https://qiita.com/rukihena/items/82266ed3a43e4b652adb)
- [自宅状況の見える化](https://qiita.com/katsumin/items/b11da555daa506800933)

以下の目的のために、改変しました。

- Python3 で使いたい。元のコードは Python3 ではエラーになる。
- 積算電力を取得したい。瞬間の電力をとっても間欠的にしかとれないならつまらないだろうと考えたが、この点についてはあまり意味が無かったかもしれない。

Python は不慣れなので、改善できる箇所が山ほどあるはずです。

開発環境

- 電力会社: 東京電力
- Wi-SUN インタフェース: テセラ・テクノロジー株式会社 RL7023 Stick-D/IPS
- ホスト: Raspberry Pi 2 Model B Rev 1.1
- OS: Raspbian GNU/Linux 10 (buster)
- Python: 3.7.3
