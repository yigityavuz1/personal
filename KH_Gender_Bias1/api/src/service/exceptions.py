class LLMExtractionError(Exception):
    def __init__(self, sentence: str):
        self.sentence = sentence

    def __str__(self):
        return f"The GPT-4 could not extract any phrases from the sentence: {self.sentence}"

