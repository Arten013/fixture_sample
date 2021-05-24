# pytest fixtureの地味だけど重要な部分について

[この記事](https://blog.hoxo-m.com/entry/fixture_scope)のサンプルコードが入ったリポジトリ

# ディレクトリ構成

- main.md: 本文
- mymodule: テストで使うための架空のモジュール
- tests: テストファイル
    - test_sectionX: X節と対応したテストの入ったスクリプト。コメントで大まかに分けてあります。test_sub内にも一部入ってます。
- その他: 省略

# 実行方法

1. テストのルードディレクトリに移動
2. pytestをpip install
3. pytestコマンドを実行