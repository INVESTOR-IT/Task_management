from app.core.config import logger

import asyncio
import random


async def process_task_logic(task_id: str) -> tuple[bool, str]:
    '''
    Имимтирую асинхронную обработку задач
    '''

    logger.info(f'Worker: выпоняю {task_id} задачу')
    await asyncio.sleep(work_duration := random.randint(3, 20))

    if random.random() < 0.8:
        result = f'Задача {task_id} завершена за {work_duration} сек.'
        logger.info(result)
        return True, result
    else:
        error_message = f'Задача {task_id} не завершилась за {work_duration}'
        logger.error(error_message)
        return False, error_message
