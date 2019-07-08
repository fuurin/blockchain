import request, sys
from blockchain import Blockchain
from flask import Flask, jsonify, request
from uuid import uuid4 # ユニークなIDを生成，バージョン4

app = Flask(__name__)


# ブロックの終わりに追加される特別なトランザクションのrecipientのID
node_identifier = str(uuid4()).replace('-', '')

blockchain = Blockchain()

@app.route('/transactions/new', methods=['POST'])
def new_transactions():
    """
    新しいトランザクションを追加
    """
    values = request.get_json()

    # 必要な値があるかをチェック
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400
    
    # 新しいトランザクションを作ってブロックに追加
    index = blockchain.new_transaction(
        values['sender'], 
        values['recipient'],
        values['amount']
    )

    response = {'message': f'Transaction appended into the block {index}'}
    return jsonify(response), 201
    

@app.route('/mine', methods=['GET'])
def mine():
    """
    新しいブロックを採掘する
    ここでいう採掘とは，おそらくプルーフの条件を満たすようなハッシュ値を
    見つけるということなのかと思う
    """

    # 次のプルーフを見つけるためPoWアルゴリズムを使用
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # ブロックという区切りを示すための特別なトランザクションを追加
    # プルーフを見つけたことに対する報酬を得る
    # 送信者は，採掘者がコインを採掘したことを表すために0とする
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1
    )

    # チェーンに新しいブロックを加え，そのブロックの採掘を完了する
    block = blockchain.new_block(proof)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def full_chain():
    """
    ブロックチェーンを全て返す
    """
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_node():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: invalid node list", 400

    for node in nodes:
        blockchain.register_node(node)
    
    response = {
        'message': 'New node added',
        'total_nodes': list(blockchain.nodes),
    }

    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': "Chain is replaced",
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Chain is already up-to-date',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


# port 5000でサーバを起動する
if __name__ == '__main__':
    port = sys.argv[1] or 5000
    app.run(host='0.0.0.0', port=int(port))
