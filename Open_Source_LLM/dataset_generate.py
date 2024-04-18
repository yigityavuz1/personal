from dataset.alpaca.alpaca_turkish import AlpacaGPT4TurkishDataset
from dataset.alpaca.alpaca_cross import AlpacaGPT4CrossDataset
import argparse
from utils import set_environment, set_logging

set_environment()
set_logging()

dataset_dict = {
    "alpaca-gpt4-tr": AlpacaGPT4TurkishDataset,
    "alpaca-gpt4-cross": AlpacaGPT4CrossDataset,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_type", type=str, required=True)
    parser.add_argument("--repo", type=str, required=True)
    parser.add_argument("--save_path", type=str, required=True)
    args = parser.parse_args()

    # Because this is a generation, local is always False
    dataset = dataset_dict[args.dataset_type](args.repo, False)
    dataset.load()
    dataset.generate()
    dataset.save(args.save_path)