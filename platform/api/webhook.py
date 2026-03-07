"""
Webhook API
Приём сообщений от MAX мессенджера
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from platform.bot_engine import dispatcher

router = APIRouter(tags=["Webhook"])
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


@router.post("/webhook/{bot_token}")
@limiter.limit("100/minute")
async def webhook(
    bot_token: str,
    request: Request
) -> Dict[str, Any]:
    """
    Webhook для приёма сообщений от MAX мессенджера

    Этот endpoint вызывается MAX'ом когда пользователь:
    - Отправляет сообщение боту
    - Нажимает кнопку (callback query)
    - Отправляет команду (например /start)

    Args:
        bot_token: Токен бота (из URL)
        request: FastAPI Request с телом в формате MAX Update

    Returns:
        Dict с результатом обработки

    Example MAX Update:
    ```json
    {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": "user_id",
                "username": "username",
                "first_name": "John"
            },
            "chat": {
                "id": "chat_id",
                "type": "private"
            },
            "text": "Hello, bot!",
            "date": 1234567890
        }
    }
    ```

    Документация MAX Bot API: https://max.team/docs/bots (если доступна)
    """
    try:
        # Получаем тело запроса
        update = await request.json()

        logger.info(
            f"Webhook received: bot={bot_token[:10]}..., "
            f"update_id={update.get('update_id')}"
        )

        # Обрабатываем через dispatcher
        result = await dispatcher.handle_update(bot_token, update)

        if not result.get("ok"):
            logger.error(f"Failed to process update: {result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Unknown error")
            )

        return result

    except ValueError as e:
        # Бот не зарегистрирован
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        # Неожиданная ошибка
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/webhook/{bot_token}")
async def webhook_info(bot_token: str) -> Dict[str, Any]:
    """
    Получить информацию о webhook

    Полезно для проверки что webhook настроен правильно

    Args:
        bot_token: Токен бота

    Returns:
        Dict с информацией
    """
    is_registered = dispatcher.is_registered(bot_token)

    return {
        "bot_token": bot_token[:10] + "...",
        "registered": is_registered,
        "webhook_url": f"/webhook/{bot_token}",
        "status": "active" if is_registered else "not_registered"
    }


@router.get("/webhook/_stats")
async def webhook_stats() -> Dict[str, Any]:
    """
    Статистика dispatcher'а

    Показывает сколько ботов зарегистрировано и активно

    **Только для отладки!** В продакшене нужно защитить паролем.
    """
    return dispatcher.get_stats()


# ============================================
# ТЕСТОВЫЙ ENDPOINT (для разработки)
# ============================================

@router.post("/webhook/_test/{bot_token}")
async def test_webhook(
    bot_token: str,
    message_text: str = "Test message"
) -> Dict[str, Any]:
    """
    Тестовый endpoint для отправки fake сообщения

    Используется для тестирования без реального MAX API

    Args:
        bot_token: Токен бота
        message_text: Текст тестового сообщения

    Example:
    ```bash
    curl -X POST "http://localhost:8000/webhook/_test/mock_token_12345678?message_text=Hello"
    ```
    """
    # Создаём fake update
    fake_update = {
        "update_id": 999999,
        "message": {
            "message_id": 1,
            "from": {
                "id": "test_user",
                "username": "test_user",
                "first_name": "Test"
            },
            "chat": {
                "id": "test_chat",
                "type": "private"
            },
            "text": message_text,
            "date": 1234567890
        }
    }

    logger.info(f"Test webhook: bot={bot_token[:10]}..., text={message_text}")

    # Обрабатываем через dispatcher
    result = await dispatcher.handle_update(bot_token, fake_update)

    return result
