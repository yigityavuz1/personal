import joblib
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

def detect_language(text, vectorizer_path=None, model_path=None):
    """
    Loads the vectorizer and the model from given paths, then detects language of input text whether it is english or turkish. (1 = tr, 0 = en)
    :param text: input string to detect language
    :param vectorizer_path: path to the vectorizer .joblib file
    :param model_path: path to the model .joblib file
    :return: detected_language (1 = tr, 0 = en)
    """
    # Load given vectorizer
    vectorizer = joblib.load(open(vectorizer_path, 'rb'))

    # Load given language detection model
    model = joblib.load(open(model_path, 'rb'))

    # Transform input text into features using given vectorizer
    # The input for the transform method should be a list of strings, so we put the text into a list
    X = vectorizer.transform([text])

    # Detect whether the input text is English or Turkish. (1 = tr, 0 = en)
    detected_language = model.predict(X)

    return detected_language[0]
