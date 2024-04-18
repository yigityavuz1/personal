import yaml
import os


def set_environment():
    with open("config/defaults.yaml") as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
    for k, v in cfg['Environment'].items():
        os.environ[k] = str(v)


def set_logging():
    import transformers
    with open("config/defaults.yaml") as f:
        cfg = yaml.load(f, Loader=yaml.FullLoader)
        log_level = cfg['Logging']['TransformersLogLevel'].lower()

    if  log_level == 'info':
        transformers.logging.set_verbosity_info()
    elif log_level == 'warning':
        transformers.logging.set_verbosity_warning()
    elif log_level == 'error':
        transformers.logging.set_verbosity_error()
    elif log_level == 'debug':
        transformers.logging.set_verbosity_debug()
    else:
        raise ValueError("Invalid TransformersLogLevel in config.yaml")

