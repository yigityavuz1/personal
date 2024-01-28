import logging
import os


def get_logger(
        name: str, _id: str = None, export: bool = False, log_file: str = None
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            f"%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        if export:
            if not _id:
                os.makedirs("/app/logs/", exist_ok=True)
            else:
                os.makedirs(f"/app/logs/{_id}", exist_ok=True)
                _id += "/"
            fh = logging.FileHandler(log_file.format(_id))
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

    return logger
