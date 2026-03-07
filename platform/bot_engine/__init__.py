"""
Bot Engine
Единый движок для обработки сообщений всех ботов платформы
"""
from platform.bot_engine.dispatcher import MultiTenantDispatcher, dispatcher

__all__ = ["MultiTenantDispatcher", "dispatcher"]
