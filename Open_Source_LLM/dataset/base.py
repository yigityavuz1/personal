from datasets import load_dataset, load_from_disk

import logging

class BaseDataset:
    def __init__(self, path, local):
        self.path = path
        self.data = None
        self.local = local

    def load(self):
        if not self.local:
            self.data = load_dataset(self.path, "default")
        else:
            self.data = load_from_disk(self.path)

    @staticmethod
    def map_to_chat_template(examples):
        raise NotImplementedError

    def split(self, test_size=0.1):
        if self.data['valid'] is None:
            self.data = self.data['train'].train_test_split(test_size=test_size, seed=42, shuffle=True)
            self.data['valid'] = self.data['test']
            del self.data['test']
        else:
            logging.warning("Validation set already exists. Skipping split.")

    def generate(self):
        self.data = self.data.map(self.map_to_chat_template, batched=True)

    def save(self, path):
        self.data.save_to_disk(path)

    def download(self):
        raise NotImplementedError