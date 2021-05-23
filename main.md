# Fixtureを効率的に作るためのスコープの話
こんにちは。ホクソエムサポーターのPython担当、藤岡です。
最近はデータエンジニア見習いとしてBI周りを触っています。

今回はpytestのfixtureについての記事です。
スコープ周りの話を中心に、fixtureを効率的に作成するための機能を紹介していこうと思います。

## 1. 前書き
- 基礎的なことに関しては[この記事](https://www.m3tech.blog/entry/pytest-summary)にとても簡潔にまとまっているので、こちらをまず読むのがオススメです。とても良い記事です。
- pytestは独自の書き方を持ち込んでいるライブラリです。その機能を使いこなすと「綺麗」なコードにはなりますが、反面それは使われている機能を知らない人にとってはこの上なく読みにくいものです。やりすぎて可読性が下がらないよう、用法用量を守りましょう。
- 本稿の環境は[こちらのリポジトリ](https://github.com/Arten013/fixture_sample)からcloneできますので、試しながら読んでみてください。

## 2. fixtureとusefixtures
pytestのfixtureの機能としてもっとも基本的なものがオブジェクトの生成です。
例えば、

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

といったようなものです。
おそらく、fixtureのイメージとして一番強いのがこの使い方ではないでしょうか。

しかし、実際はそれだけに止まりません。

例えば、機械学習のコードなどでは乱数が使用されているため、結果を固定するには乱数シードの固定が必要です。
こうした処理をfixtureとして用意するとこのようになります。

```python
import random

@fixture
def set_seed():
    random.seed(0)
```

このように、何も返さず、テストにただ前処理を施すのもfixtureの機能なのです。

さて、少し定義の話をします。
"test fixture"を辞書で引くと「試験装置」と出てきます。
[Wikipedia](https://en.wikipedia.org/wiki/Test_fixture)の言葉を借りればtest "environment"、つまり環境です。

なので、入出力のオブジェクトはもちろんのこと、乱数シードの固定、データベースやサーバへのコネクション（のスタブ）の確立、さらにファイルやフォルダの生成/削除などもfixtureであり、fixtureデコレータを使って実装するべきものです。

話を戻しますが、何かしらの処理だけをして値を返さないfixtureはテストケースの引数として渡すのは不適切です。
こういった場面では、`usefixtures`デコレータを使うことでテスト前にfixtureの処理を実行することができます。

```python
@pytest.mark.usefixtures('set_seed')
def test_fix_seed():
    rand1 = random.random()
    ramdom.set_seed(0)
    rand2 = random.random()
    assert rand1 == rand2
```

しかし、この例ではシードの固定を内部でも一回やっていてイマイチです。

というわけで、今度はシードの初期化をさせるのではなく、その処理をするコールバックを返すことで解決します。

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

関数を返すのは公式でも使用されているテクニックです。
例えば、predefinedなfixtureには一時ディレクトリのパスを返す`tmpdir`があるのですが、
一時ディレクトリを生成するためのコールバック`tmpdir_factory`もあります。

もちろん、fixtureではなくヘルパ関数として`seed_setter`を定義して呼び出すという選択肢もあるので、ケースバイケースで選択しましょう。
上記の例ではヘルパ関数の方がいいと思いますが、乱数シードの固定が至る所で使われるならばfixtureの方がいいです。

他に`usefixtures`を使う例として、`unittest`の`patch`があります。
下のサンプルコードでは、`mymodule.ObjectWithDB`の`connect`メソッドをMagicMockに置き換えています。
これを`usefixtures`で宣言すれば、データベースコネクションをスキップして`ObjectWithDB`を使えます。

```python
from unittest.mock import patch
from mymodule import ObjectWithDB

@fixture
def ignore_db_connection():
    with patch("mymodule.ObjectWithDB.connect"):
        yield
```

`usefixture`はとても便利ですが、テストケース以外では使えないという点に注意してください。
例えば、以下のようなことはできません (エラーは吐きませんが、無視されます)。

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

これは再現性の観点からは良いのですが、その反面オーバーヘッドが発生します。

例えば、テスト用のデータセットにアクセスするfixtureがあったとします。
一回に3秒の初期化がかかったとして、1,000のテストケースで使用されるとしたら、それだけで50分かかります。

そこで、試しにテスト実行順をstart -> test1 -> test2 > endというように変更してみます。
そのためには、`pytest.fixture`の引数に`scope="session"`を加えます。

```python
@fixture(scope="session")
def foo_session():
    print("start")
    yield
    print("end")
```

実行してみると、意図した通りの挙動になっていることが分かります。
このように、fixtureにおける実行タイミング、つまりいつ`yield`（`return`）に入って、いつ`yield`に戻る（`return`の場合は特になし）なのかを決定するためには、
`scope`というパラメータを設定します。

変数のスコープと混同するので、本稿ではそれぞれ変数スコープ、fixtureスコープと呼ぶことにします。

fixtureスコープは以下の4種類があり、それぞれ変数スコープとよく似た入れ子状のブロックとしてのまとまりを持ちます。

- そのテストケース自身のみ((`parametrize`で複数回実行される場合には、その一回の実行を指します))を含む最小単位であるfuntionスコープ (デフォルト)。
- クラスの内部の変数スコープと対応する、classスコープ。
- 一つのモジュールの変数スコープと対応するmoduleスコープ。
- 全てのテストケース/fixtureを含むsession（package）スコープ。

functionスコープ以外では、最初に`yield`した（`return`した）結果をキャッシュして同じスコープのテストに渡して、そのスコープの終端で`yield`後の処理を実施しています。
これは、`test_1`と`test_2`のそれぞれについて、同じオブジェクトIDのオブジェクトが渡されていることからも確かめられます。

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

わからない場合は実行してみましょう。すると、以下の行を含むログが表示されます。
```
E       assert [1, 3] == [3, 1]
E         At index 0 diff: 1 != 3
```

どうやら、`ids`が`test_ids_sort`の中でソートされた後にそのまま`test_ids_pop`に渡されてしまっているようです。
キャッシュした値がうっかり破壊的処理によって書き変わってしまう、典型的なバグです。

今回の場合は簡単に分かる話ですが、実際にこのバグに遭遇する場合はたいていもっと厄介です。
現実には、同じfixtureを使うテストが別々のスクリプトに点在している場合もあります。
加えて、テストがバグっている場合、元のソースがバグっている場合の間で区別がしづらいのも問題です。
それだけではなく、例えば、`test_ids_pop`だけをテストしてやると通ってしまいます（PyCharmであれば簡単にできます）。

こんな事例を想像指定みてください。
あなたは新しくテストをいくつか追加しました。それらが通ることは確認済みです。しかしpushしてさあ帰るぞと支度をしていたら、CIからエラーが返ってきている。
どうやら、まったく弄っていない別のテストがエラーを吐いているようだ。でもそのテストだけを走らせてみるとやっぱり動いている……。
残業中なら、`xfail`を付けて逃げたくなるような話です。

言うまでもないですが、この依存関係を利用するなんてことは論外です。

他にも、広いfixtureスコープのfixtureから狭いfixtureスコープのfixtureは呼び出せないという制限があるので、
無闇に広げるとこの制限に引っかかります。
例えば、以下のfixtureを呼び出すとエラーを吐きます。

```python
@fixture
def foo():

@fixture(scope="session")
def foo_session(foo):
    ...
```

ただ、どうしてもfixtureスコープを広げたい場合もありますので、
その場合には以下の事項に気をつけましょう。

- 渡すオブジェクトがimmutableかどうか。
    - 極力immutableなオブジェクトを渡す。
    - mutableオブジェクトならば、テストやテストされる関数等で破壊的なメソッドを呼ばないように細心の注意を払う。
- immutableオブジェクトでも、DBコネクション等の外部参照をするfixtureを渡す場合には、それがテストごとにリセットされるかどうか（リセット用fixtureを作って常に使うようにするのも手です。）。

## 5. fixtureの可用範囲
これまでの例ではコードスニペットだけを扱ってきましたが、実際のテストスクリプトは複数のテストケース、それらをもつクラス、果ては複数のスクリプトにまたがります。
fixtureのスコープだけでなく、fixtureの可用範囲、変数でいうところの変数スコープを理解する必要が出てきます。

まず、基本的には「テストケースが定義された場所」を基準に考えればOKです。

例えば、以下の例では`test_foo`と`test_foo_2`は同じような挙動をします。
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
ここで注意してほしいのが、あくまでグローバル領域であり、これはテストケースの関数ブロックの**外側**の話です。

クラスが絡むと、この差がもう少しはっきり出てきます。

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

クラスブロックでは特殊な名前解決が行われるので、例えば`bar_fixt_2`からクラス変数`bar_var`は参照できません。
上の例では`type`(`self`)を通じてアクセスしています。
一方、クラスブロック内では（当たり前ですが）参照可能なので、クラス変数`ref_bar_var`の定義時に`bar_var`を参照できます。

fixtureについても、`bar_var`同様に直接参照可能です。
テストケースの定義されたブロックで名前解決をしていることが、先ほどの例よりもはっきりと分かります。

さて、さらにテストが大きくなってきた場合を考えてみましょう。
多くのテストケースが作成され、似たようなfixtureが複数のスクリプトに定義されるようになってしまいます。
当然、fixtureを使い回したいという欲求が出てきます（よね？）。

pytestでは、スクリプト間でfixtureを使い回すための仕組みが提供されています。
試しに、conftest.pyという名前のファイルをテストフォルダ直下に作成し、
その中にfixtureを入れてみてください（もちろん、サンプルリポジトリにも用意されています）。
すると、そのfixtureを全てのテストで使うことができます。

conftest.pyは便利なのですが、fixtureをどんどん作成していると次第に汚くなってきます。

なので、conftest.pyをある程度分割することをオススメします。
conftest.py内で定義されたfixtureの使用可能な範囲は、正確には「conftest.pyの定義されたフォルダとそのサブディレクトリのテスト」です。
なので、テストをサブディレクトリに分割してその中にconftest.pyを作成すれば分割できます。
また、conftest.pyはいわゆるグローバルなオブジェクトが作られてしまうので、
ある程度狭い範囲で利用可能になるように（とはいえconftest.pyが増えすぎないように）
するのがベストかなと思います。

余談ですが、筆者は他のファイルで定義したfixtureをconftest.pyでimportすることでconftest.pyを
綺麗に保っていたことがあります。
しかし、fixtureのimportは**非推奨**であり今後のバージョンでの**動作は保証されない**ので注意してください
((本稿を書いてて初めて知りました。名案だと思って、趣味のプロジェクトでは結構使ってたんですけどね……。))。

## 6. fixtureの連鎖と階層構造
fixtureで一番~~楽しい~~便利な機能がfixtureの連鎖です。
本稿を書いた理由の半分が本節の内容です。

pytestでは、fixtureを定義する際にfixtureを入力として受け取ることが可能です。
知っている方も多いと思うので、ここまでの例でもいくつかの例でこの機能を利用していました。
機能としてはシンプルかつよく知られていると思うのですが、本節ではその細かい部分に突っ込んでいきます。

### 6.1 fixtureの循環/再帰エラー
fixtureからfixtureを呼び出すことで、fixtureどうしに有向の依存関係が発生します。
そして、この依存関係を解決する必要があるので、循環や再帰があってはいけません。

```python
# 循環の例
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

# 再帰の例
@pytest.fixture
def recursive_fixture(recursive_fixture):
    ...

def test_recursive_fixture(cycle_3):
    ...
```

上記の例を実行すると、
```
recursive dependency involving fixture '***' detected
```
といったようなエラーが発生します。

testからfixtureを呼び出す場合と同様に、fixtureからfixtureを呼び出す場合でも
変数スコープやconftest.pyの階層関係が成立します。
なお、最上位にあたるfixtureはルートディレクトリのconftest内のfixtureかと思いきや、
実はpredefinedなfixtureです((pluginまで絡んでくるとどうなるのかは未検証ですが、おそらく同様の扱いになるかと思います。pluginの間で循環とかありえるのでしょうか？　気になるところです))。

### 6.2 同名fixtureの連鎖
次に、下の例のように同じ名前のfixtureを複数作って、一つ目で二つ目を上書きするような例を考えてみます。

```python
@fixture
def foo_fixture():
    return [1, 2, 3]

@fixture
def foo_fixture(foo_fixture):
    return foo_fixture + [4, 5]
```

残念ながら、上の例はエラーとなってしまいます。

同一のfixtureを定義した場合、この部分が含まれたモジュールがimportされた場合と同様に、後に定義された方が前に定義された方を上書きしてしまいます。
つまり、一つ目の`foo_fixture`が無視されて二つ目の`foo_fixture`が自身を再帰的に入力としていることになり、上記のエラーが出てしまいます。

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

上の例では、`TestFoo.foo_fixture`がglobal領域の`foo_fixture`を引数にとり、それを変形したものを返しています。
このように複数の変数領域に分けることで二つのfixtureの間に上位下位関係が成立して循環と重複がなくなり、
下位のfixtureから上位のfixtureを利用することが可能となります。

「別の名前のfixtureでいいじゃないか……」という意見もあるかと思いますし、役割が大きく変化してしまう場合などにはそれが正しいです。
一方、似通った名前のfixtureを量産することや、fixtureの名前が具体化するにつれて長くなってしまうのは
あまり良くありません((テストケースについてはそれ自身を呼び出すこともないので長い名前もOKです))。

### 6.3 親子クラス間での同名fixtureの連鎖
では、最後にクラスを継承した場合はどうなるでしょうか。

以下の例は、ベースとなるfixtureとテストケースを用意して、
それを継承したテストを作成することで様々なパターンのテストの実装を省力化する試みです。

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
これはベースクラスの`inherit_fixture`が上書きされるので、再帰的なfixtureとなってエラーを吐きます。

修正案としては、まずそもそもfixtureについてはベースクラスで定義しないでおいて、
ベースクラスをテスト対象から外すような修正をするのが一番だと思います。

どうしてもfixtureも使い回したい場合、
以下のようにベースのfixtureを外に出してしまうという方法があります。

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

テストでクラスの継承を使い始めるとややこしくなるので、テストケースを継承するようなクラスはそうそう作るべきではないという意見もあります。
とはいえ、自分はこれもケースバイケースであり必要に応じて継承は使うべきだと考えているので、あえてここで紹介しました。

# 7.まとめ
pytestについて自分の好きな話をなんとかテーマに沿って選抜して、まとめてみました。
正直、半年前まではpytestを含めてテストを書くのは好きではなかったのですが、
pytestのテクニカルな部分に触れるうちに段々と楽しくなっていき~~やりすぎることも多々あり~~ました。

また、テストを何度も書くうちにテストをしやすいようなコードを書く意識がついて、
自分の設計能力も上がったのは嬉しい誤算でした。

実務的にテストを書くという行為は、納期やリソース、チームのルールなど、非常に多くのパラメータが絡み合っており、
経験から程よいテストをいい感じに書くという、理論や知識よりも経験が求められる世界だと考えています。
なので、Pythonを書く全ての人が、まずはpytestの楽しさに気づいて、テストを書く機会を増やし、
やがてこの世界からレガシーコードが減っていけばと切に切に切に願っています。