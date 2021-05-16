# 実践pytest.fixture
こんにちは。ホクソエムサポーターのPython担当、藤岡です。

今回はpytestのfixtureについて、なるべく実践的な内容を中心に解説していきます。

## 1. 前書き
- 基礎的なことに関しては[この記事](https://www.m3tech.blog/entry/pytest-summary)にとても簡潔にまとまっているので、こちらをまず読むのがオススメです。とても良い記事だと思います。
- 今回の記事ではpytestの基礎に加えて、変数スコープについての知識が必要です。
- pytestは独自の書き方を持ち込んでいるライブラリです。その機能を使いこなすと「綺麗」なコードにはなりますが、反面それは使われている機能を知らない人にとってはこの上なく読みにくいものです。やりすぎて可読性が下がらないよう、用法用量を守りましょう。~~もしくはpytestを布教しましょう。~~

## 2. setup
本稿の環境はこちらのリポジトリからcloneできますので、試しながら読んでみてください。

test fixtureについて辞書を引くと試験装置と出てきます。
pytestにおいてもその例に漏れません。
fixtureの基本的な使い方を続けているとfixtureがテストオブジェクトを指す言葉だと誤解していきますが、
本来は試験装置、wikipediaの言葉を借りればtest environmentです。

ソフトウェア開発におけるテストは用途も形態も様々ですが、基本的には、
あるソフトウェアもしくはその一部の処理について、ある値の入力によって特定の値が返されること、もしくは特定の振る舞いをすること、もしくはその両方を確かめる行為です。
本稿では、上記の定義でテストについて扱っていきます。

pytestにおいては、test environmentとはテストコードを実装するためのリソースが整っているという環境のことに見えます。
この環境では、例えば入出力のオブジェクト、その前提となるデータベースやサーバへのコネクションなどが必要に応じて引き出せます。
特に後者についてはコンストラクト/デストラクトに面倒な処理が挟まるので、毎度毎度テストごとに生成していたらテストコードも工数もみるみる膨んでいきます。
こうしたオブジェクトは、fixtureの最も基本的な使い方である、`fixture`デコレータを付けるだけで簡単に実装できます。

```python
@fixture
def values():
    return [2, 1, 3]

@fixture
def sorted_values():
    return [1, 2, 3]

def test_sorted(values, sorted_values):
    assert sorted(values) == sorted_values
```

繰り返しになりますが、fixtureとは環境であって、単なるオブジェクトに止まりません。
例えば、機械学習のコードなどでは乱数が処理に使用されているため、結果を固定するには乱数シードの固定が必要です。
こうした処理をfixtureとして用意するとこのようになります。

```python
import random

@fixture
def set_seed():
    random.seed(0)
```

このような処理をするfixtureは値を返さないため、テストケースの引数として渡すのは不適切でしょう。
こういった場面では、`usefixtures`デコレータを使うことでテスト前にfixtureの処理を実行することができます。

```python
@pytest.mark.usefixtures('set_seed')
def test_fix_seed():
    rand1 = random.random()
    ramdom.set_seed(0)
    rand2 = random.random()
    assert rand1 == rand2
```

シードの固定を内部でも一回やっているのはイケてませんね。
usefixtureで宣言したfixtureはテストケースの実行前に一度実行されるだけなので、
別の方法でこれを回避してみましょう。

```python
import random

@fixture
def seed_setter():
    return lambda: random.seed(0)

def test_fix_seed_2(seed_setter):
    seed_setter()
    rand1 = random.random()
    seed_setter()
    rand2 = random.random()
    assert rand1 == rand2
```

このように、処理をfixtureとして登録していつでも使用できるようにしておくという方法があります。
実際、predefinedなfixtureであるtmpdirにはtmpdir_factoryというファクトリバージョンもあるように、
関数を返すのは公式でも使用されているテクニックです。
もちろん、ヘルパ関数としてseed_setterを登録するという選択肢もあるので、
ケースバイケースで選択しましょう。
上記の例ではヘルパ関数の方がいいと思います。

他にusefixtureを使う例として、patchがあります。こちらは機械学習に限らず広く使えるテクニックです。
下のサンプルコードでは、mymodule.ObjectWithDBのconnectメソッドをMagicMockに置き換えています。
これをusefixtureで宣言すれば、データベースコネクションをスキップしてObjectWithDBを使えます。

```python
from unittest.mock import patch
from mymodule import ObjectWithDB

@fixture
def ignore_db_connection():
    with patch("mymodule.ObjectWithDB.connect"):
        yield
```

usefixtureについて注意が必要なのが、usefixtureはテストケース以外では使えないという点です。
例えば、以下のようなことはできません (エラーは吐きませんが、usefixturesが無視されます)。

```python
@fixture
@pytest.mark.usefixtures('set_seed')
def random_value():
    return random.random()
```

代わりにこうしておけばOKです。

```python
@fixture
def random_value_factory(seed_setter):
    seed_setter()
    return random.random()
```

## 3. fixtureスコープと変数スコープ
fixtureは基本的にはテストケースごとに実行されます。

以下のサンプルコードで確かめてみましょう（pytest コマンドに-s オプションを付けるとprint出力が見られます）。
```python
@fixture
def foo():
    print("start")
    yield
    print("end")

def test_1(foo):
    print("test1")

def test_2(foo):
    print("test2")
```

start -> test1 -> end -> start -> test2 > end の順番でプリントされ、テストごとにfixtureの処理が実行されています。

しかし、場合によってはこれでは不都合が起きます。

例えば、テスト用のデータセットにアクセスするfixtureがあったとします。
ファイルのIOは時間のかかる処理なので、
一回に3秒の初期化がかかったとして、1000のテストケースがあったとしたら、それだけで50分かかります。

そこで、テスト実行順をstart -> test1 -> test2 > endというように変更します。
そのためには、pytest.fixtureの引数にscope="session"と書き加えます。

```python
@fixture(scope="session")
def foo_session():
    print("start")
    yield
    print("end")
```

実行してみると、意図した通りの挙動になっていることが分かります。
このように、fixtureにおける実行タイミング、つまりいつyield（return）に入って、いつyieldに戻る（returnの場合は特になし）なのかを決定するためには、
scopeというパラメータを設定します。

変数のスコープと混同するので、それぞれ変数スコープ、fixtureスコープと呼ぶことにします。

それぞれのテストケースとfixtureは、変数スコープとよく似た、入れ子状のブロックとしてのまとまりを持ちます。
fixtureスコープは全部で以下の4種類です。

- 自分自身のみを含む最小単位である`funtion`スコープ (デフォルト)
- クラスの内部の変数スコープと対応する、`class`スコープ。
- 一つのモジュールの変数スコープと対応する`module`スコープ。
- 全てのテストケース/fixtureを含む`session`（`package`）スコープ。

これらは変数スコープとは独立しています。
例えば、モジュールのグローバル領域に定義されたfunctionスコープfixture、
クラスメソッドとして定義されたsessionスコープfixtureなどです。

これらの機能はシンプルにfixtureの返すオブジェクトをキャッシュすることで実現しています。
つまり、`test_1`, `test_2`のそれぞれについて、同じオブジェクトidのオブジェクトが渡されています。

fixtureスコープは基本的には狭いものを使用しましょう。つまり、デフォルトから変更しないのがベストです。
多少の時間的なオーバーヘッドがある場合でも、問題にならないうちは広げるべきではないでしょう。
というのも、キャッシュするという性質上、広いスコープのfixtureを使い回すとそのテスト間に
予期しない依存関係が生じてしまう恐れがあるためです。
次節以降で詳しく解説していきます。

## 4. fixtureスコープの落とし穴
さて、以下のテストには問題があります。どこか分かりますか？
```python
@fixture(scope="session")
def ids():
    return [3, 1, 4]

def test_ids_sort(ids):
    ids.sort()
    assert ids == [1, 3, 4]

def test_ids_pop(ids):
    ids.pop()
    assert ids == [3, 1]  # fail here
```

わからない場合は実行してログを見てみると分かるかもしれません。
```
E       assert [1, 3] == [3, 1]
E         At index 0 diff: 1 != 3
E         Use -v to get the full diff
```

答えは、`ids`が`test_ids_sort`の後にソートされてしまったまま`test_ids_pop`に渡されていることです。

今回の場合は少なくとも言われてしまえば分かる話ですが、
込み入ったテストではこのような依存関係は見つけづらいです。
加えて、テストがバグっている場合、元のソースがバグっている場合と区別がしづらいのも問題です。
それだけではなく、例えば、test_ids_popだけをテストしてやると通ってしまいます（PyCharmであれば簡単にできます）。
前節の最後に言及した、予期しない依存関係とはこのことです。

データサイエンス領域では、例えば巨大なarrayをfixtureとして入力するような場合をテストしていると、
ついその初期化に時間がかかってしまうからと、fixtureスコープを広げてしまうような場合が考えられます。
言うまでもないですが、この依存関係を利用するなんてことは論外です。

他にも、fixtureのscopeを広げられる範囲には制限があります。
例えば、以下のfixtureはエラーを吐きます。

```python
@fixture
def foo():

@fixture(scope="session")
def test_db():

```

ただ、どうしてもscopeを広げたい場合には、以下の事項に気をつけましょう。

- 渡すオブジェクトがimmutableかどうか（listやdictなどのmutableオブジェクトの扱いには破壊的なメソッドを呼ばないように細心の注意を払うこと）
- immutableオブジェクトでも、DBコネクション等の外部参照をするfixtureを渡す場合には、それがテストごとにリセットされるかどうか（リセット用fixtureを作って常に使うようにするのも手です。）。

## 5. fixtureの可用範囲
これまでの例では、コードスニペットだけを扱ってきましたが、実際のテストスクリプトを書く場合には、
fixtureを引っ張ってくることのできる範囲を知る必要があります。

これは、基本的には「テストケースが定義された場所」を基準に考えればOKです。

例えば、以下の例ではtest_fooとtest_foo_2は同じような挙動をします。
```python
@fixture
def foo_fixt():
    return "foo"

def test_foo(foo_fixt):
    assert foo_fixt == "foo"

foo_var = "foo"

def test_foo_2():
    assert foo_var == "foo"
```

テストケースはこのモジュールのグローバル領域に定義されているので、
同じ領域に定義された変数と同様に参照できます。
ここで注意してほしいのが、あくまでグローバル領域であり、テストケースの関数ブロックの外の話です。

classが絡むと、この差がもう少しはっきり出てきます。

```python
class TestBar():
    @fixture
    def bar_fixt(self):
        return "bar"

    def test_bar(self, bar_fixt):
        assert bar_fixt == "bar"

    bar_var = "bar"
    ref_bar_var = bar_var

    def test_bar_2(self):
        assert type(self).bar_var == "bar"
    
    @fixture
    def bar_fixt_2(self):
        return type(self).bar_var

    def test_bar_3(self, bar_fixt_2):
        assert bar_fixt_2 == "bar"
```

クラスブロックでは特殊な名前解決が行われるので、例えばbar_fixt_2からクラス変数bar_varは参照できません。
上の例ではtype(self)を通じてアクセスしています。
一方、クラスブロック内では（当たり前ですが）参照可能なので、クラス変数ref_bar_varの定義時にbar_varを参照できます。

fixtureについても、bar_var同様に直接参照可能です。
テストケースの定義されたブロックで名前解決をしていることが、先ほどの例よりもはっきりと分かります。

なお、少し趣旨からは逸れますがfixtureの元となるメソッドでも同様の名前解決が行われます（当たり前ですが...）


さて、さらにテストが大きくなってきた場合を考えてみましょう。
多くのテストケースが作成され、似たようなfixtureが複数のスクリプトに定義されるようになってしまいます。
当然、fixtureを使い回したいという欲求が出てきます（よね？）。

pytestでは、スクリプト間でfixtureを使い回すための仕組みが提供されています。
試しに、conftest.pyという名前のファイルをテストフォルダ直下に作成し、
その中にfixtureを入れてみてください。
すると、そのfixtureを全てのテストで使うことができます。

なお、他のファイルで定義したfixtureをconftest.pyでimportするだけでも動きますが、
あくまでこれは**非推奨**であり今後のバージョンでの**動作は保証されない**ので注意してください
((結構名案だと思って、趣味のプロジェクトでは使ってたんですけどね……。))。

conftest.py一つに全てのfixtureを入れてしまうと結構汚くなるのですが、
conftest.pyはある程度分割が可能です。
conftest.py内で定義されたfixtureの使用可能な範囲は、正確には「conftest.pyの定義されたフォルダとそのサブディレクトリのテスト」です。
なので、テストをサブディレクトリに分割してその中にconftest.pyを作成すれば分割できます。
むしろ、conftest.pyはいわゆるグローバルなオブジェクトが作られてしまうので、
ある程度狭い範囲で利用可能になるように（とはいえconftest.pyが増えすぎないように）
するのがベストかなと思います。

## 6. fixtureの連鎖と階層構造
本節の内容が、本稿で一番書きたかった内容です。
fixtureで一番~~楽しい~~便利な機能がfixtureの連鎖です。

pytestでは、fixtureを定義する際にfixtureを入力として受け取ることが可能です。
知っている方も多いと思うので、ここまでの例でもいくつかの例でこの機能を利用していました。
ここでは、改めて詳細や注意点について記述します。

まず、fixtureからfixtureを呼び出すことで、fixtureどうしに有向の依存関係が発生します。
そして、この依存関係を解決する必要があるので、循環や再帰があってはいけません。

```python
@fixture
def cycle_1(cycle_3):
    return cycle_3

@fixture
def cycle_2(cycle_1):
    return cycle_1

@fixture
def cycle_3(cycle_2):
    return cycle_2

def test_cycle_fixt(cycle_3):
    ...

@pytest.fixture
def recursive_fixture(recursive_fixture):
    ...

def test_recursive_fixture(cycle_3):
    ...
```

上記の例を実行すると、
```
recursive dependency involving fixture 'cycle_3' detected
```
といったようなエラーが発生します。

testからfixtureを呼び出す場合と同様に、fixtureからfixtureを呼び出す場合でも
変数スコープやconftestの階層関係が成立します。
なお、最上位にあたるfixtureはルートディレクトリのconftest内のfixtureかと思いきや、
実は定義済みのfixtureです((pluginまで絡んでくるとどうなるのかは未検証ですが、おそらく同様の扱いになるかと思います。pluginの間で循環とかありえるのでしょうか？　気になるところです))。

例外的に下のような例はエラーとなってしまいます。

```python
@fixture
def foo_fixture():
    return [1, 2, 3]

@fixture
def foo_fixture(foo_fixture):
    return foo_fixture + [4, 5]
```

同一のfixtureを定義した場合、importと同様に後に定義処理が実行された方が優先され、
それ以外は無視されます。
つまり、一つ目のfoo_fixtureが無視されて二つ目のfoo_fixtureが自身を再帰的に入力としていることになり、上記のエラーが出てしまいます。

しかし、下のように変数スコープを変えることで同じ名前のfixtureを入力とすることが可能です。

```python
@fixture
def foo_fixture():
    return [1, 2, 3]

def test_foo(foo_fixture):
    assert foo_fixture == [1, 2, 3]

class TestFoo():
    @fixture
    def foo_fixture(self, foo_fixture):
        return foo_fixture + [4, 5]

    def test_foo(self, foo_fixture):
        assert foo_fixture == [1, 2, 3, 4, 5]
```

上の例では、TestFoo.foo_fixtureがglobal領域のfoo_fixtureを引数にとり、それを変形したものを返しています。
このように複数の変数領域に分けることで二つのfixtureの間に上位下位関係が成立して循環と重複がなくなり、
下位のfixtureから上位のfixtureを利用することが可能となります。

「別の名前のfixtureでいいじゃないか……」という意見もあるかと思いますし、役割が大きく変化してしまう場合などにはむしろ名前を変えるべきでしょう。
一方、似通った名前のfixtureを量産することや、fixtureの名前が具体化するにつれて長くなってしまうのは
あまり良くありません((テストケースについてはそれ自身を呼び出すこともないので長い名前もOKです))。

では、最後にクラスを継承した場合はどうなるでしょうか。

以下の例は、ベースとなるテストケースを用意して、
それを継承したテストを作成することでテストケース自体を使いまわそうという試みです。

```python
class TestBase():
    EXPECTED = [1, 2]

    @fixture
    def inherit_fixture(self):
        return [1, 2]

    def test_inherit_fixture(self, inherit_fixture):
        assert inherit_fixture == self.EXPECTED


class TestInherit(TestBase):
    EXPECTED = [1, 2, 3, 4]

    @fixture
    def inherit_fixture(self, inherit_fixture):
        return inherit_fixture + [3, 4]
```

TestInherit.test_inherit_fixtureは通るでしょうか？

正解は、「通らない」です。
これはベースクラスのinherit_fixtureが上書きされるので、再帰的なfixtureとなってエラーを吐きます。

修正案としては、以下のようにベースのfixtureを外に出してしまうという方法があります。

```python
@fixture
def inherit_fixture():
    return [1, 2]

class TestBase():
    EXPECTED = [1, 2]

    def test_inherit_fixture(self, inherit_fixture):
        assert inherit_fixture == self.EXPECTED

class TestInherit(TestBase):
    EXPECTED = [1, 2, 3, 4]

    @fixture
    def inherit_fixture(self, inherit_fixture):
        return inherit_fixture + [3, 4]
```

そもそもpytestではclassの継承を使い始めるとややこしくなるので、そもそもテストケースを継承するようなクラスはそうそう作るべきではないと思います。
とはいえ、これもケースバイケースであり、必要であれば継承をすることは許されると考えているので、
あえてここで紹介しました。

# 7.まとめ
前回に引き続き、今回も有名なライブラリの重箱の隅をつついてみました。
正直、半年前まではテストを書くのは好きではなかったのですが、
PyTestのテクニカルな部分に触れるうちに段々と楽しくなっていき~~やりすぎることも多々あり~~ました。

実務的にテストを書くという行為は、納期やリソース、チームのルールなど、非常に多くのパラメータが絡み合っており、
経験から程よいテストをいい感じに書くという、理論や知識よりも経験が求められる世界だと考えています。
まずはPytestの楽しさに触れて、テストを書く機会を増やしていただき
この世界からレガシーコードを駆逐していただければと切に切に切に願っています。