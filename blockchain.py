import hashlib
import json
from time import time

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_votes = []
        self.create_block(previous_hash='0')

    def create_block(self, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'votes': self.current_votes,
            'previous_hash': previous_hash,
            'hash': ''
        }
        block['hash'] = self.hash(block)
        self.current_votes = []
        self.chain.append(block)
        return block

    def add_vote(self, voter_id, candidate):
        self.current_votes.append({
            'voter_id': hashlib.sha256(voter_id.encode()).hexdigest(),
            'candidate': candidate
        })

    def hash(self, block):
        encoded_block = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()

    def last_block(self):
        return self.chain[-1]