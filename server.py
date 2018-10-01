import json
import uuid
import requests
import urllib
from socketIO_client import SocketIO, BaseNamespace
from multiprocessing import Process
from pymongo import MongoClient
from flask import Flask, request, session, redirect, render_template
import sys
from flask_cors import CORS
sys.path.insert(0,'/home/mvogel/yadacoin')
from yadacoin import TransactionFactory, TU, BU, Config, Mongo, Peers

app = Flask(__name__)
app.debug = True
app.secret_key = '23ljk2l9a08sd7f09as87df09as87df3k4j'
CORS(app)

app.template_folder = '/home/mvogel/dev/yadaserviceprovider/templates'
try:
    with open('config.json') as f:
        Config.from_dict(json.loads(f.read()))
    print Config.to_json()
except:
    print "you must generate a config and save it to a file named config.json"
Peers.init()
Mongo.init()

@app.route('/', methods=['GET', 'POST'])
def home():
    session.setdefault('id', str(uuid.uuid4()))

    if request.method == 'POST':
        bulletin_secret = request.form.get('bulletin_secret', '')
        if not bulletin_secret:
            return redirect('/?error')
        # generate a transaction which contains a signin message containing the current sessions identifier
        txn = TransactionFactory(
            bulletin_secret=bulletin_secret,
            public_key=Config.public_key,
            private_key=Config.private_key,
            signin=session.get('id'),
            fee=0.01
        ).transaction

        # send the transaction to our own serve instance, which saves it to miner_transactions
        # the miner looks in miner_transactions to include in a block when it finds a new block
        for peer in Peers.peers:
            print peer.host, peer.port
            requests.post(
                "http://{host}:{port}/newtransaction".format(
                    host=peer.host,
                    port=peer.port
                ),
                txn.to_json(),
                headers={"Content-Type": "application/json"}
            )
        return redirect('/?bulletin_secret=%s' % urllib.quote_plus(bulletin_secret))
    elif request.method == 'GET':
        bulletin_secret = request.args.get('bulletin_secret', '')
        rid = TU.generate_rid(bulletin_secret)
        txns = BU.get_transactions_by_rid(rid, rid=True)

        txns2 = BU.get_transactions_by_rid(rid, rid=True, raw=True)
        half1 = False
        half2 = False
        for txn in txns:
            if txn['public_key'] == Config.public_key:
                half1 = True
        for txn in txns2:
            if txn['public_key'] != Config.public_key:
                half2 = True
        registered = half1 and half2
        sent, received = BU.verify_message(rid, session['id'])
        session['loggedin'] = received
        return render_template(
            'index.html',
            session_id=str(session.get('id')),
            registered=str(registered),
            sent=str(sent),
            received=str(received),
            loggedin=str(session['loggedin']),
            bulletin_secret=str(bulletin_secret),
            rid=str(rid)
        )
    else:
        return redirect('/')

app.run(host=Config.serve_host, port=Config.serve_port, debug=True)