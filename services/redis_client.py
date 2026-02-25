"""
🚀 Redis Cache Service for CyberArena

Кэширование доступности компьютеров для ускорения проверки в 5-10 раз.
TTL (время жизни кэша) = 5 минут по умолчанию.

Использование:
    cache = RedisCache()
    await cache.connect()
    
    # Проверить кэш
    data = await cache.get_available_pcs(club_id=1, date="2024-02-02")
    
    # Сохранить в кэш
    await cache.set_available_pcs(club_id=1, date="2024-02-02", data=[...])
    
    # Очистить при бронировании
    await cache.invalidate_club(club_id=1)
"""

import redis.asyncio as redis
import json
import logging
from typing import Optional, List, Any
from config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Асинхронный Redis клиент для кэширования данных о доступности.
    
    Падение Redis НЕ должно ломать приложение — используем graceful degradation.
    """
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.connected = False
        self.default_ttl = 300  # 5 минут
    
    async def connect(self) -> bool:
        """
        Подключение к Redis. Возвращает False если Redis недоступен.
        Приложение продолжит работать без кэша.
        """
        try:
            self.redis = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=getattr(settings, 'REDIS_PORT', 6379),
                db=getattr(settings, 'REDIS_DB', 0),
                decode_responses=True,
                socket_connect_timeout=2  # Не ждать долго при старте
            )
            # Проверяем подключение
            await self.redis.ping()
            self.connected = True
            logger.info("Redis connected successfully")
            return True
        except Exception as e:
            logger.warning(f"Redis unavailable, running without cache: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Закрыть соединение с Redis."""
        if self.redis:
            await self.redis.close()
            self.connected = False
    
    def _make_key(self, prefix: str, club_id: int, date: str = None) -> str:
        """Генерация ключа кэша."""
        if date:
            return f"cyberarena:{prefix}:{club_id}:{date}"
        return f"cyberarena:{prefix}:{club_id}"
    
    # ==================== AVAILABLE PCS ====================
    
    async def get_available_pcs(self, club_id: int, date: str) -> Optional[List[dict]]:
        """
        Получить кэшированный список доступных компьютеров.
        
        Args:
            club_id: ID клуба
            date: Дата в формате "YYYY-MM-DD"
            
        Returns:
            List[dict] если кэш есть, None если нет или ошибка
        """
        if not self.connected:
            return None
        
        try:
            key = self._make_key("available_pcs", club_id, date)
            data = await self.redis.get(key)
            
            if data:
                logger.debug(f"🎯 Cache HIT: {key}")
                return json.loads(data)
            
            logger.debug(f"❌ Cache MISS: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set_available_pcs(
        self, 
        club_id: int, 
        date: str, 
        data: List[dict], 
        ttl: int = None
    ) -> bool:
        """
        Сохранить список доступных компьютеров в кэш.
        
        Args:
            club_id: ID клуба
            date: Дата в формате "YYYY-MM-DD"
            data: Список компьютеров
            ttl: Время жизни в секундах (по умолчанию 5 минут)
            
        Returns:
            True если успешно, False при ошибке
        """
        if not self.connected:
            return False
        
        try:
            key = self._make_key("available_pcs", club_id, date)
            ttl = ttl or self.default_ttl
            
            await self.redis.setex(key, ttl, json.dumps(data, ensure_ascii=False))
            logger.debug(f"💾 Cached: {key} (TTL={ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def invalidate_club(self, club_id: int) -> bool:
        """
        Очистить весь кэш для клуба (при бронировании или изменении).
        
        Использует pattern matching для удаления всех ключей клуба.
        """
        if not self.connected:
            return False
        
        try:
            pattern = self._make_key("*", club_id) + "*"
            
            # Используем SCAN для безопасного удаления (не блокирует Redis)
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break
            
            logger.info(f"🗑️ Invalidated {deleted} cache keys for club {club_id}")
            return True
            
        except Exception as e:
            logger.error(f"Redis invalidate error: {e}")
            return False
    
    # ==================== ЗАНЯТЫЕ ЧАСЫ ====================
    
    async def get_occupied_hours(self, club_id: int, computer_id: str, date: str) -> Optional[List[int]]:
        """Получить кэшированные занятые часы для компьютера."""
        if not self.connected:
            return None
        
        try:
            key = f"cyberarena:occupied:{club_id}:{computer_id}:{date}"
            data = await self.redis.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Redis get_occupied error: {e}")
            return None
    
    async def set_occupied_hours(
        self, 
        club_id: int, 
        computer_id: str, 
        date: str, 
        hours: List[int],
        ttl: int = 120  # 2 минуты для занятости — чаще обновляется
    ) -> bool:
        """Сохранить занятые часы в кэш."""
        if not self.connected:
            return False
        
        try:
            key = f"cyberarena:occupied:{club_id}:{computer_id}:{date}"
            await self.redis.setex(key, ttl, json.dumps(hours))
            return True
        except Exception as e:
            logger.error(f"Redis set_occupied error: {e}")
            return False
    
    # ==================== HEALTH CHECK ====================
    
    async def health_check(self) -> dict:
        """
        Проверка здоровья Redis для /health endpoint.
        """
        if not self.connected:
            return {"status": "disconnected", "ok": False}
        
        try:
            await self.redis.ping()
            info = await self.redis.info("memory")
            return {
                "status": "healthy",
                "ok": True,
                "used_memory": info.get("used_memory_human", "unknown")
            }
        except Exception as e:
            return {"status": f"error: {e}", "ok": False}


# Глобальный экземпляр кэша (singleton)
cache = RedisCache()
