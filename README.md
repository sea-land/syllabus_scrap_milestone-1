# README.md

## はじめに

このプログラムは早稲田大学のシラバスをスクレイピングし、科目データと科目ノートの素を作成するものです。
このプログラムは「Docker」というソフトを使用することにより、Mac と Windows の両方で動作します。
(一部の Mac で動作しないことが確認されています。2,3 回実行して動作しなかったら部室のパソコンか Windows を使っている人にお願いをしてください)

**最終更新日時: 2024 年 11 月 13 日**

## 手順

### 1. Docker デスクトップをインストール

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/)の公式サイトにアクセスします。
2. ダウンロードボタンをクリックし、インストールファイルをダウンロードします。
3. ダウンロードしたファイルをダブルクリックしてインストールを開始します。
4. インストールが完了したら、Docker Desktop を起動します。(この先の操作がすべて終わるまでソフトを起動したままにしてください)

### 2. GitHub アカウントを作成

1. [GitHub](https://github.com/)の公式サイトにアクセスします。
2. 画面右上の「Sign up」ボタンをクリックします。
3. 必要な情報を入力してアカウントを作成します。
4. メールアドレスの確認が求められるので、指示に従って確認を完了させます。
   (デジタル部署のアカウントで作成済みなのでコンソールマニュアルから ID を確認してください)

### 3. このプロジェクトをダウンロード (GitHub の使い方がわかる人は git clone で大丈夫です)

1. このページ上部の緑色で<span style="color: green;">Code</span>と書かれているボタンをクリックします。
2. Download Zip をクリックします。
3. Windows ならエクスプローラー、Mac なら Finder でダウンロードした Zip ファイルを解凍します。
4. 解凍したフォルダ(.zip ではない)のパスをコピーします。以下手順です。
   #### Windows
   エクスプローラーで解凍したフォルダ(zip でない)を Shift キーを押しながら右クリック　 → 　ターミナルで開くをクリック
   #### Mac
   ファインダーで解凍したフォルダ(zip ではない)を右クリック(トラックパッドなら二本指でクリック)　 → 　 フォルダに新規ターミナルというボタンが出現するのでクリック
5. ls というコマンドを実行して結果が以下のようになっていれば大成功です。出力結果が違う場合は 4.からやり直してください。

```bash
❯ ls
README.md		docker-compose.yml   py_context		work
```

### 4. プログラムを起動

1. そのまま 以下のコマンドを実行します。
   ```bash
   start "http://localhost:7900/?autoconnect=1&resize=scale&password=secret";docker-compose up --build
   ```
2. これにより、デフォルトのブラウザに VNC が起動します。これでスクレイピングは開始されました。
3. 開いて 5 秒後くらいに Connect ボタンを押すと実際にスクレイピングをしている様子が見られます。通信状況や大学のサーバーの理由により一時読み込みに時間がかかりフリーズすることがありますが気長に待ちましょう。

### 5. `app.txt`のログを確認

1. 以下のコマンドでログファイルを表示します。ログファイルは定期的に更新されますのでそのまま待っていてください。

   ```bash
   <!-- Windowsの人用 -->
   Get-Content -Path "work/log/app.txt" -Wait -tail 10 -Encoding UTF8

   <!-- Macの人用 -->
   tail -f work/log/app.txt
   ```

2. `==========スクレイピング開始==========`というメッセージが表示され、スクレイピングが開始されたことを確認します。
3. `==========スクレイピング完了==========`というメッセージが表示され、スクレイピングが完了したことを確認します。
4. ログに`ERROR`が含まれている箇所は出力データに載っていないのでエラーメッセージを確認して必要であれば手動で追加してください。

### 6. 結果の確認

1. スクレイピングの結果は、以下のようにファイルが出力されます。(約 1 時間かかります)
   ` data/出力年月/科目データ/{学部}_科目データ.csv`
   `data/出力年月/科目ノートの素/{学部}_科目ノートの素.csv `
2. data という名前のファイルを開いて結果を確認してください。

---

以上の手順に従って設定を完了し、スクレイピングを実行してください。手順通りに進めれば必ずできるはずなので何かエラーが起きたとしても焦らずにもう一度やってみましょう。

### 7. トラブルシューティング

1 番の原因は「ネットワーク環境」です。
Docker は PC の環境に依存しない(mac であろうが、windows であろうが、どんな OS のバージョンでも変わらない)ので、基本は動きます。

### 8. 出力データとアルゴリズム

1. 出力データは csv ファイルです。このファイルは excel で開くことができます。
2. 出力時のデータは["科目区分", "授業 ID", "学部", "年度", "コースコード", "科目名", "カモクメイ", "担当教員", "フリガナ", "学期", "曜日時限", "学年", "単位数", "教室", "キャンパス", "科目キー", "科目クラス", "使用言語", "授業形式", "レベル", "授業形態", "授業概要", "シラバス URL"]となっています。
3. 担当教員は/の数を数えて 2 つ以上ならオムニバスと書き換えてあります。1 つの場合は/を・に自動で置き換えます。
4. 担当教員の名前がすべてカタカナの場合はスペースを.で置き換えます。
5. 授業形式はコースコードの末尾のアルファベットを取得して自動入力されます。
6. 科目名と担当教員は Python のライブラリを使ってフリガナを出力しますが結果は保証できないので 2 重チェックをしてください(特に索引部署)
7. 後から付け加えるのがとても大変なので取得できる情報はほぼすべて出力しています。必要なところだけ使ってください。ただし科目ノートを作る際は列を消すのではなく非表示にして作業をするようにしてください。一部の情報はこの後コンソールツールで使用するので残してほしいです。

制作
leo271
HKobayashi2003 (46 期)

修正・変更
sea-land (47 期)
