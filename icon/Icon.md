---
title: Macでシェルスクリプトを .appアイコン化する方法
tags: MacOSX
author: KurosawaTsuyoshi
slide: false
url: https://qiita.com/KurosawaTsuyoshi/items/425cd484e8d7759af460
---

JMeter をインストールした際、起動シェルをアイコン化したかったので備忘録。

### Automator を起動

Launchpad を起動し、検索窓から「Automator」を探して起動します。
![01.png](https://qiita-image-store.s3.amazonaws.com/0/104535/ecc64fa2-d215-3ae9-04ce-322f6f6b3f5e.png)

Automator のメニューから、ファイル ＞ 新規 で、「アプリケーション」を選択します。  
![02.png](https://qiita-image-store.s3.amazonaws.com/0/104535/dce2a69c-b1c5-1006-71d4-e940622e7cd4.png)

リストから「シェルスクリプトを実行」を選択し、ドラッグします。  
![03.png](https://qiita-image-store.s3.amazonaws.com/0/104535/35776a93-990d-66d0-b632-e977be56c063.png)

### 起動シェルのパス指定

起動するシェルのフルパスを指定します。
Finder を開いて対象のシェル（今回は jmeter.sh)を、枠内にドラッグでも構いません。
なお、デフォルトで ”cat” と文字が挿入されてるのでこれは削除しましょう。  
![04.png](https://qiita-image-store.s3.amazonaws.com/0/104535/ad2d5a3b-be42-800b-bfee-1446c1c92fd0.png)

### 起動シェルを確認して変更します。

シェルスクリプトの先頭行を確認し、起動するシェルを指定します。
jmeter.sh の先頭行は `#! /bin/sh` なので、プルダウンから"/bin/sh"を選択します。
![05.png](https://qiita-image-store.s3.amazonaws.com/0/104535/26a69e8b-1ac2-235b-9135-11a2545c4f49.png)

### .app の保存

メニューから、ファイル　＞　保存 を選択します。
格納先は「アプリケーション」とし、好きな名前を指定して保存します。  
![06.png](https://qiita-image-store.s3.amazonaws.com/0/104535/cdfb5a97-0c71-4aa2-be03-67807fd2dae3.png)

### .app の起動確認

これでアプリとして追加されてるので、Launchpad などから起動してみましょう。

### アイコンの変更

作成したアプリのアイコンは「Automater」のアイコンとなってます。
アプリを Ctrl キーを押しながらクリックし「情報を見る」を選択します。
![07.png](https://qiita-image-store.s3.amazonaws.com/0/104535/88c0a4b2-246c-49e4-1c6a-80da686b5448.png)

ボックスの上部にアイコンに、直接画像をドロップすると変更できます。
今回は Apache JMeter のロゴを HP からドロップしました。

![08.png](https://qiita-image-store.s3.amazonaws.com/0/104535/5dd67956-46c8-69f7-2b37-8ce9ea7dfe8f.png)

これで閉じて変更完了です。
![09.png](https://qiita-image-store.s3.amazonaws.com/0/104535/e3f2c385-7c63-901a-86db-bc276678784b.png)

以上です。
