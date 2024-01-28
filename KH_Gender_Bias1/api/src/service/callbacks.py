import asyncio
from logging import Logger


def task_done_callback(task: asyncio.Task, logger: Logger, results: list):
    try:
        name = task.get_name()
        result = task.result()
        logger.info(f"Successfully completed chain-{name}")
        results.append(result)
    except Exception as e:
        logger.error(f"Chain-{name} raised an exception, the error is: '{str(e)}'")

