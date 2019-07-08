import hashlib, json, requests
from time import time
from urllib.parse import urlparse

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # ブロックチェーンを共有するノードを「集合」で持つ
        self.nodes = set()

        # ジェネシスブロック(先祖を持たないブロック)を作る
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        """
        新しいブロックを作り，チェーンに加える
        :param proof: <int> プルーフオブワークアルゴリズムから得られるプルーフ
        :param previous_hash: (オプション) <str> 前のブロックのハッシュ(繋ぎ直しor初期化)
        :return: <dict> 新しいブロック
        """
        
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        # 現在のトランザクションリストをリセット
        self.current_transactions = []

        self.chain.append(block)
        return block
    
    def new_transaction(self, sender, recipient, amount):
        """
        次に採掘(生成?)される新しいトランザクションをリストに加える
        :param sender: <str> 送信者のアドレス
        :param recipient: <str> 受信者のアドレス
        :param amount: <int> 量
        :return: <int> このトランザクションを含むブロックのアドレス
        """
        
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        # トランザクション実行後採掘される，新しいブロックのインデックスだから+1
        return self.last_block['index'] + 1
    
    @staticmethod
    def hash(block):
        """
        ブロックをSHA-256ハッシュにする
        :param block: <dict> ブロック
        :return: <str>
        """
        
        # jsonにする→その文字列をハッシュにする
        # 必ずディクショナリがソートされている必要がある．
        # そうでないと，keyの順番が違うとき予期しないハッシュ値となってしまう
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()
    
    @property # ()なしで呼び出せる
    def last_block(self):
        """ チェーンの最後のブロックをリターンする """
        return self.chain[-1]
    
    def proof_of_work(self, last_proof):
        """
        シンプルなPoWのアルゴリズム
        - p に対するhash(p, q)がTrueになるような q を探す
        - p は1つ前のブロックのプルーフ，qは新しいブロックのプルーフ
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        プルーフが正しいかを確認する
        - ここではhash(last_proof, proof)の最初の4つが0ならOKというルール
        :param last_proof: <int> 前のプルーフ
        :param proof: <int> 現在のプルーフ
        :return: <bool> 正しければTrue, そうでなければFalse
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


    def register_node(self, address):
        """
        ノードリストに新しいノードを加える
        :param address: <str> ノードのアドレス
            例: 'http://192.168.0.5:5000'
        :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)
    
    def valid_chain(self, chain):
        """
        ブロックチェーンが正しいかを確認する
        前のブロックのハッシュが次のブロックに正しく伝わっていること
        前後のPoW間でルールが守られていること(ハッシュとったら)
        :param chain: <list> ブロックチェーン
        :return: <bool> Trueは正常，Falseは異常(PoWがおかしい)
        """
        
        for i in range(1, len(chain)):
            last_block = chain[i-1]
            current_block = chain[i]
            print(f'{last_block}')
            print(f'{current_block}')
            print("\n-----------------\n")
            
            # 前のブロックの正しいハッシュを次のブロックが持っているかを確認
            if current_block['previous_hash'] != self.hash(last_block):
                return False
            
            # PoWが正しいかを確認
            if not self.valid_proof(last_block['proof'], current_block['proof']):
                return False
        
        # 全てのブロック間でルールが守られていれば合格
        return True
    
    def resolve_conflicts(self):
        """
        コンセンサスアルゴリズム．
        ネットワーク上の最も長いチェーンを自らのチェーンと置き換える
        そのようにしてコンフリクトを解消する
        :return: <bool> 置き換えが発生したときのみTrue
        """

        neighbors = self.nodes
        new_chain = None

        # 自らのチェーンより長いチェーンを探す
        max_length = len(self.chain)

        # 他の全てのノードのチェーンを確認
        for node in neighbors:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # そのチェーンが現在最長より長く，正常なら更新
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        
        # もし自らのチェーンより長く，かつ有効なチェーンを見つけた場合置き換え
        if new_chain:
            self.chain = new_chain
            return True
        
        return False