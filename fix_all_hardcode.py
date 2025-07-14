#!/usr/bin/env python3
"""
Комплексное исправление ВСЕХ проблем с хардкодом.
Автоматически исправляет все 115 нарушений и добавляет переводы.
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set

class ComprehensiveHardcodeFixer:
    def __init__(self):
        # Полный маппинг всех найденных проблем
        self.hardcode_mapping = {
            # Admin conversations
            "📢 **Предпросмотр рассылки:**\\n\\n": "broadcast.preview_title",
            "Отправить это сообщение всем пользователям?": "broadcast.confirm_question",
            "📤 **Отправка рассылки...**\\n\\nПожалуйста, подождите...": "broadcast.sending_message",
            "✅ **Рассылка завершена!**\\n\\n": "broadcast.completed_title",
            "📊 **Результаты:**\\n": "broadcast.results_title",
            "❌ **Рассылка отменена**\\n\\nНичего не было отправлено.": "broadcast.cancelled_message",
            "❌ **Создание рассылки отменено**\\n\\nВсе данные очищены.": "broadcast.creation_cancelled",
            "✅ Да, отправить": "broadcast.confirm_yes",
            "❌ Нет, отменить": "broadcast.confirm_no",
            
            # Rate limit handler
            "общих команд": "rate_limit.general_commands",
            "запросов в друзья": "rate_limit.friend_requests",
            "изменений настроек": "rate_limit.settings_changes",
            "поиска друзей": "rate_limit.friend_discovery",
            "админских команд": "rate_limit.admin_commands",
            "нажатий кнопок": "rate_limit.button_clicks",
            "_Лимиты защищают бот от перегрузки._": "rate_limit.protection_note",
            
            # Error handler
            "❌ Не удалось получить статистику пользователей.": "errors.stats_failed",
            "📊 **Статистика пользователей**\\n\\n": "admin.stats_title",
            "🚫 **Превышен лимит запросов**\\n\\n": "errors.rate_limit_title",
            "Вы отправляете команды слишком часто.\\n": "errors.rate_limit_message",
            "🔒 **Доступ запрещен**\\n\\nЭта команда доступна только администраторам.": "errors.admin_access_denied",
            
            # Config commands
            "⏰ **Установить временное окно**\\n\\n": "config.window_title",
            "Использование: `/window HH:MM-HH:MM`\\n\\n": "config.window_usage",
            "Примеры:\\n": "config.examples_title",
            "• `/window 09:00-18:00` - с 9 утра до 6 вечера\\n": "config.window_example1",
            "• `/window 22:00-06:00` - с 10 вечера до 6 утра": "config.window_example2",
            "Формат: `HH:MM-HH:MM`\\n": "config.window_format",
            "Пример: `/window 09:00-22:00`": "config.window_format_example",
            "✅ **Временное окно обновлено!**\\n\\n": "config.window_updated",
            "⏰ Новое время: ": "config.window_new_time",
            "Теперь уведомления будут приходить только в это время.": "config.window_updated_note",
            "📊 **Установить частоту уведомлений**\\n\\n": "config.frequency_title",
            "Где N - интервал в минутах между уведомлениями.\\n\\n": "config.frequency_description",
            "Примеры:\\n": "config.examples_title",
            "• `/freq 60` - каждый час\\n": "config.freq_example_60",
            "• `/freq 120` - каждые 2 часа\\n": "config.freq_example_120_long",
            "• `/freq 30` - каждые 30 минут": "config.freq_example_30",
            "❌ Минимальный интервал: 5 минут\\n\\n": "config.freq_min_error",
            "Пример: `/freq 30`": "config.freq_min_example",
            "❌ Максимальный интервал: 1440 минут (24 часа)\\n\\n": "config.freq_max_error",
            
            # Friends callbacks
            "Вопрос": "common.question",
            "Без имени": "common.no_name",
            "Неизвестно": "common.unknown",
            "неизвестен": "common.unknown_user",
            "ожидает ответа": "friends.awaiting_response",
            "❌ Отклонить": "friends.decline_button",
            "✅ Принять": "friends.accept_button",
            
            # Question templates
            "Что делаешь?": "questions.default_question",
            "друг": "questions.friend",
            "Рабочие задачи": "questions.work_tasks",
            "💼 Над чем работаешь сейчас?": "questions.work_current",
            "Для отслеживания рабочих проектов": "questions.work_description",
            "Обучение": "questions.learning",
            "📚 Что изучаешь?": "questions.learning_current",
            "Для отслеживания процесса обучения": "questions.learning_description",
            "Цели дня": "questions.daily_goals",
            "🎯 Какие цели на сегодня?": "questions.daily_goals_current",
            "Для планирования дня": "questions.daily_goals_description",
            "Здоровье": "questions.health",
            "🏃‍♂️ Как дела со здоровьем?": "questions.health_current",
            "Отслеживание самочувствия": "questions.health_description",
            "Эмоции": "questions.emotions",
            "😊 Какое настроение?": "questions.emotions_current",
            "Отслеживание эмоционального состояния": "questions.emotions_description",
            "Утренний чекин": "questions.morning_checkin",
            "🌅 Как начинается день?": "questions.morning_current",
            "Для планирования дня": "questions.morning_description",
            "Вечерний чекин": "questions.evening_checkin",
            "🌙 Как прошёл день?": "questions.evening_current",
            "Для подведения итогов дня": "questions.evening_description",
            "Продуктивность": "questions.productivity",
            "⚡ Что сделал продуктивного?": "questions.productivity_current",
            "Для отслеживания результатов": "questions.productivity_description",
            "Спорт": "questions.sport",
            "🏋️‍♂️ Тренировался сегодня?": "questions.sport_current",
            "Для отслеживания тренировок": "questions.sport_description",
            "Чтение": "questions.reading",
            "📖 Что читаешь?": "questions.reading_current",
            "Для отслеживания прочитанного": "questions.reading_description",
            "Творчество": "questions.creativity",
            "🎨 Чем занимаешься творчески?": "questions.creativity_current",
            "Для развития креативности": "questions.creativity_description",
            "Отношения": "questions.relationships",
            "💕 Как дела с близкими?": "questions.relationships_current",
            "Для укрепления отношений": "questions.relationships_description",
            "Отдых": "questions.rest",
            "🏖️ Как отдыхаешь?": "questions.rest_current",
            "Для баланса работы и отдыха": "questions.rest_description",
            "Саморазвитие": "questions.self_development",
            "🌱 Над чем работаешь в себе?": "questions.self_development_current",
            "Для личностного роста": "questions.self_development_description",
            "Основной": "questions.main",
            "🌆 Как прошёл день? Что удалось сделать?": "questions.main_question",
            "Для общего отслеживания активности": "questions.main_description",
            
            # Language detector
            "Автоматически": "language.auto",
            "Русский": "language.russian",
            "Английский": "language.english",
            "Испанский": "language.spanish",
            "Китайский": "language.chinese",
            
            # Multi question scheduler
            "Неизвестно": "common.unknown",
            "неизвестен": "common.unknown_user",
            
            # Admin handlers
            "❌ Не удалось получить статистику пользователей.": "errors.stats_failed",
            "📊 **Статистика пользователей**\\n\\n": "admin.stats_title",
            "общих команд": "rate_limit.general_commands",
            
            # Question manager
            "Вопрос": "common.question",
            "Основной": "questions.main",
        }
        
        # Комплексные переводы для всех ключей
        self.translation_keys = self.create_comprehensive_translations()
    
    def create_comprehensive_translations(self) -> Dict[str, Dict[str, str]]:
        """Создает комплексные переводы для всех ключей."""
        return {
            # Broadcast
            "broadcast.preview_title": {
                "ru": "📢 **Предпросмотр рассылки:**\n\n",
                "en": "📢 **Broadcast Preview:**\n\n",
                "es": "📢 **Vista Previa de Difusión:**\n\n"
            },
            "broadcast.confirm_question": {
                "ru": "Отправить это сообщение всем пользователям?",
                "en": "Send this message to all users?",
                "es": "¿Enviar este mensaje a todos los usuarios?"
            },
            "broadcast.sending_message": {
                "ru": "📤 **Отправка рассылки...**\n\nПожалуйста, подождите...",
                "en": "📤 **Sending broadcast...**\n\nPlease wait...",
                "es": "📤 **Enviando difusión...**\n\nPor favor espere..."
            },
            "broadcast.completed_title": {
                "ru": "✅ **Рассылка завершена!**\n\n",
                "en": "✅ **Broadcast completed!**\n\n",
                "es": "✅ **¡Difusión completada!**\n\n"
            },
            "broadcast.results_title": {
                "ru": "📊 **Результаты:**\n",
                "en": "📊 **Results:**\n",
                "es": "📊 **Resultados:**\n"
            },
            "broadcast.cancelled_message": {
                "ru": "❌ **Рассылка отменена**\n\nНичего не было отправлено.",
                "en": "❌ **Broadcast cancelled**\n\nNothing was sent.",
                "es": "❌ **Difusión cancelada**\n\nNo se envió nada."
            },
            "broadcast.creation_cancelled": {
                "ru": "❌ **Создание рассылки отменено**\n\nВсе данные очищены.",
                "en": "❌ **Broadcast creation cancelled**\n\nAll data cleared.",
                "es": "❌ **Creación de difusión cancelada**\n\nTodos los datos borrados."
            },
            "broadcast.confirm_yes": {
                "ru": "✅ Да, отправить",
                "en": "✅ Yes, send",
                "es": "✅ Sí, enviar"
            },
            "broadcast.confirm_no": {
                "ru": "❌ Нет, отменить",
                "en": "❌ No, cancel",
                "es": "❌ No, cancelar"
            },
            
            # Rate limit
            "rate_limit.general_commands": {
                "ru": "общих команд",
                "en": "general commands",
                "es": "comandos generales"
            },
            "rate_limit.friend_requests": {
                "ru": "запросов в друзья",
                "en": "friend requests",
                "es": "solicitudes de amistad"
            },
            "rate_limit.settings_changes": {
                "ru": "изменений настроек",
                "en": "settings changes",
                "es": "cambios de configuración"
            },
            "rate_limit.friend_discovery": {
                "ru": "поиска друзей",
                "en": "friend discovery",
                "es": "descubrimiento de amigos"
            },
            "rate_limit.admin_commands": {
                "ru": "админских команд",
                "en": "admin commands",
                "es": "comandos de admin"
            },
            "rate_limit.button_clicks": {
                "ru": "нажатий кнопок",
                "en": "button clicks",
                "es": "clics de botón"
            },
            "rate_limit.protection_note": {
                "ru": "_Лимиты защищают бот от перегрузки._",
                "en": "_Rate limits protect the bot from overload._",
                "es": "_Los límites protegen el bot de sobrecarga._"
            },
            
            # Config
            "config.window_title": {
                "ru": "⏰ **Установить временное окно**\n\n",
                "en": "⏰ **Set Time Window**\n\n",
                "es": "⏰ **Establecer Ventana de Tiempo**\n\n"
            },
            "config.window_usage": {
                "ru": "Использование: `/window HH:MM-HH:MM`\n\n",
                "en": "Usage: `/window HH:MM-HH:MM`\n\n",
                "es": "Uso: `/window HH:MM-HH:MM`\n\n"
            },
            "config.examples_title": {
                "ru": "Примеры:\n",
                "en": "Examples:\n",
                "es": "Ejemplos:\n"
            },
            "config.window_example1": {
                "ru": "• `/window 09:00-18:00` - с 9 утра до 6 вечера\n",
                "en": "• `/window 09:00-18:00` - from 9 AM to 6 PM\n",
                "es": "• `/window 09:00-18:00` - de 9 AM a 6 PM\n"
            },
            "config.window_example2": {
                "ru": "• `/window 22:00-06:00` - с 10 вечера до 6 утра",
                "en": "• `/window 22:00-06:00` - from 10 PM to 6 AM",
                "es": "• `/window 22:00-06:00` - de 10 PM a 6 AM"
            },
            "config.window_format": {
                "ru": "Формат: `HH:MM-HH:MM`\n",
                "en": "Format: `HH:MM-HH:MM`\n",
                "es": "Formato: `HH:MM-HH:MM`\n"
            },
            "config.window_format_example": {
                "ru": "Пример: `/window 09:00-22:00`",
                "en": "Example: `/window 09:00-22:00`",
                "es": "Ejemplo: `/window 09:00-22:00`"
            },
            "config.window_updated": {
                "ru": "✅ **Временное окно обновлено!**\n\n",
                "en": "✅ **Time window updated!**\n\n",
                "es": "✅ **¡Ventana de tiempo actualizada!**\n\n"
            },
            "config.window_new_time": {
                "ru": "⏰ Новое время: ",
                "en": "⏰ New time: ",
                "es": "⏰ Nuevo tiempo: "
            },
            "config.window_updated_note": {
                "ru": "Теперь уведомления будут приходить только в это время.",
                "en": "Now notifications will come only at this time.",
                "es": "Ahora las notificaciones llegarán solo en este momento."
            },
            "config.frequency_title": {
                "ru": "📊 **Установить частоту уведомлений**\n\n",
                "en": "📊 **Set Notification Frequency**\n\n",
                "es": "📊 **Establecer Frecuencia de Notificaciones**\n\n"
            },
            "config.frequency_description": {
                "ru": "Где N - интервал в минутах между уведомлениями.\n\n",
                "en": "Where N is the interval in minutes between notifications.\n\n",
                "es": "Donde N es el intervalo en minutos entre notificaciones.\n\n"
            },
            "config.freq_example_60": {
                "ru": "• `/freq 60` - каждый час\n",
                "en": "• `/freq 60` - every hour\n",
                "es": "• `/freq 60` - cada hora\n"
            },
            "config.freq_example_120_long": {
                "ru": "• `/freq 120` - каждые 2 часа\n",
                "en": "• `/freq 120` - every 2 hours\n",
                "es": "• `/freq 120` - cada 2 horas\n"
            },
            "config.freq_example_30": {
                "ru": "• `/freq 30` - каждые 30 минут",
                "en": "• `/freq 30` - every 30 minutes",
                "es": "• `/freq 30` - cada 30 minutos"
            },
            "config.freq_min_error": {
                "ru": "❌ Минимальный интервал: 5 минут\n\n",
                "en": "❌ Minimum interval: 5 minutes\n\n",
                "es": "❌ Intervalo mínimo: 5 minutos\n\n"
            },
            "config.freq_min_example": {
                "ru": "Пример: `/freq 30`",
                "en": "Example: `/freq 30`",
                "es": "Ejemplo: `/freq 30`"
            },
            "config.freq_max_error": {
                "ru": "❌ Максимальный интервал: 1440 минут (24 часа)\n\n",
                "en": "❌ Maximum interval: 1440 minutes (24 hours)\n\n",
                "es": "❌ Intervalo máximo: 1440 minutos (24 horas)\n\n"
            },
            
            # Errors
            "errors.stats_failed": {
                "ru": "❌ Не удалось получить статистику пользователей.",
                "en": "❌ Failed to get user statistics.",
                "es": "❌ No se pudieron obtener las estadísticas de usuarios."
            },
            "errors.rate_limit_title": {
                "ru": "🚫 **Превышен лимит запросов**\n\n",
                "en": "🚫 **Rate limit exceeded**\n\n",
                "es": "🚫 **Límite de solicitudes excedido**\n\n"
            },
            "errors.rate_limit_message": {
                "ru": "Вы отправляете команды слишком часто.\n",
                "en": "You are sending commands too frequently.\n",
                "es": "Estás enviando comandos con demasiada frecuencia.\n"
            },
            "errors.admin_access_denied": {
                "ru": "🔒 **Доступ запрещен**\n\nЭта команда доступна только администраторам.",
                "en": "🔒 **Access denied**\n\nThis command is only available to administrators.",
                "es": "🔒 **Acceso denegado**\n\nEste comando solo está disponible para administradores."
            },
            
            # Admin
            "admin.stats_title": {
                "ru": "📊 **Статистика пользователей**\n\n",
                "en": "📊 **User Statistics**\n\n",
                "es": "📊 **Estadísticas de Usuarios**\n\n"
            },
            
            # Questions
            "questions.default_question": {
                "ru": "Что делаешь?",
                "en": "What are you doing?",
                "es": "¿Qué estás haciendo?"
            },
            "questions.friend": {
                "ru": "друг",
                "en": "friend",
                "es": "amigo"
            },
            "questions.main": {
                "ru": "Основной",
                "en": "Main",
                "es": "Principal"
            },
            "questions.main_question": {
                "ru": "🌆 Как прошёл день? Что удалось сделать?",
                "en": "🌆 How was your day? What did you manage to do?",
                "es": "🌆 ¿Cómo fue tu día? ¿Qué lograste hacer?"
            },
            "questions.main_description": {
                "ru": "Для общего отслеживания активности",
                "en": "For general activity tracking",
                "es": "Para seguimiento general de actividad"
            },
            
            # Language
            "language.auto": {
                "ru": "Автоматически",
                "en": "Automatically",
                "es": "Automáticamente"
            },
            "language.russian": {
                "ru": "Русский",
                "en": "Russian",
                "es": "Ruso"
            },
            "language.english": {
                "ru": "Английский",
                "en": "English",
                "es": "Inglés"
            },
            "language.spanish": {
                "ru": "Испанский",
                "en": "Spanish",
                "es": "Español"
            },
            "language.chinese": {
                "ru": "Китайский",
                "en": "Chinese",
                "es": "Chino"
            },
            
            # Common
            "common.question": {
                "ru": "Вопрос",
                "en": "Question",
                "es": "Pregunta"
            },
            "common.no_name": {
                "ru": "Без имени",
                "en": "No name",
                "es": "Sin nombre"
            },
            "common.unknown": {
                "ru": "Неизвестно",
                "en": "Unknown",
                "es": "Desconocido"
            },
            "common.unknown_user": {
                "ru": "неизвестен",
                "en": "unknown",
                "es": "desconocido"
            },
            
            # Friends
            "friends.awaiting_response": {
                "ru": "ожидает ответа",
                "en": "awaiting response",
                "es": "esperando respuesta"
            },
            "friends.decline_button": {
                "ru": "❌ Отклонить",
                "en": "❌ Decline",
                "es": "❌ Rechazar"
            },
            "friends.accept_button": {
                "ru": "✅ Принять",
                "en": "✅ Accept",
                "es": "✅ Aceptar"
            },
            
            # Все остальные ключи из question templates
            "questions.work_tasks": {
                "ru": "Рабочие задачи",
                "en": "Work tasks",
                "es": "Tareas de trabajo"
            },
            "questions.work_current": {
                "ru": "💼 Над чем работаешь сейчас?",
                "en": "💼 What are you working on now?",
                "es": "💼 ¿En qué estás trabajando ahora?"
            },
            "questions.work_description": {
                "ru": "Для отслеживания рабочих проектов",
                "en": "For tracking work projects",
                "es": "Para seguimiento de proyectos de trabajo"
            },
            "questions.learning": {
                "ru": "Обучение",
                "en": "Learning",
                "es": "Aprendizaje"
            },
            "questions.learning_current": {
                "ru": "📚 Что изучаешь?",
                "en": "📚 What are you studying?",
                "es": "📚 ¿Qué estás estudiando?"
            },
            "questions.learning_description": {
                "ru": "Для отслеживания процесса обучения",
                "en": "For tracking learning process",
                "es": "Para seguimiento del proceso de aprendizaje"
            },
            "questions.daily_goals": {
                "ru": "Цели дня",
                "en": "Daily goals",
                "es": "Objetivos del día"
            },
            "questions.daily_goals_current": {
                "ru": "🎯 Какие цели на сегодня?",
                "en": "🎯 What are your goals for today?",
                "es": "🎯 ¿Cuáles son tus objetivos para hoy?"
            },
            "questions.daily_goals_description": {
                "ru": "Для планирования дня",
                "en": "For daily planning",
                "es": "Para planificación diaria"
            },
            "questions.health": {
                "ru": "Здоровье",
                "en": "Health",
                "es": "Salud"
            },
            "questions.health_current": {
                "ru": "🏃‍♂️ Как дела со здоровьем?",
                "en": "🏃‍♂️ How is your health?",
                "es": "🏃‍♂️ ¿Cómo está tu salud?"
            },
            "questions.health_description": {
                "ru": "Отслеживание самочувствия",
                "en": "Tracking well-being",
                "es": "Seguimiento del bienestar"
            },
            "questions.emotions": {
                "ru": "Эмоции",
                "en": "Emotions",
                "es": "Emociones"
            },
            "questions.emotions_current": {
                "ru": "😊 Какое настроение?",
                "en": "😊 What's your mood?",
                "es": "😊 ¿Cuál es tu estado de ánimo?"
            },
            "questions.emotions_description": {
                "ru": "Отслеживание эмоционального состояния",
                "en": "Tracking emotional state",
                "es": "Seguimiento del estado emocional"
            },
            "questions.morning_checkin": {
                "ru": "Утренний чекин",
                "en": "Morning check-in",
                "es": "Check-in matutino"
            },
            "questions.morning_current": {
                "ru": "🌅 Как начинается день?",
                "en": "🌅 How is your day starting?",
                "es": "🌅 ¿Cómo está empezando tu día?"
            },
            "questions.morning_description": {
                "ru": "Для планирования дня",
                "en": "For daily planning",
                "es": "Para planificación diaria"
            },
            "questions.evening_checkin": {
                "ru": "Вечерний чекин",
                "en": "Evening check-in",
                "es": "Check-in vespertino"
            },
            "questions.evening_current": {
                "ru": "🌙 Как прошёл день?",
                "en": "🌙 How was your day?",
                "es": "🌙 ¿Cómo fue tu día?"
            },
            "questions.evening_description": {
                "ru": "Для подведения итогов дня",
                "en": "For daily review",
                "es": "Para revisión diaria"
            },
            "questions.productivity": {
                "ru": "Продуктивность",
                "en": "Productivity",
                "es": "Productividad"
            },
            "questions.productivity_current": {
                "ru": "⚡ Что сделал продуктивного?",
                "en": "⚡ What did you accomplish?",
                "es": "⚡ ¿Qué lograste hacer?"
            },
            "questions.productivity_description": {
                "ru": "Для отслеживания результатов",
                "en": "For tracking results",
                "es": "Para seguimiento de resultados"
            },
            "questions.sport": {
                "ru": "Спорт",
                "en": "Sports",
                "es": "Deportes"
            },
            "questions.sport_current": {
                "ru": "🏋️‍♂️ Тренировался сегодня?",
                "en": "🏋️‍♂️ Did you work out today?",
                "es": "🏋️‍♂️ ¿Hiciste ejercicio hoy?"
            },
            "questions.sport_description": {
                "ru": "Для отслеживания тренировок",
                "en": "For tracking workouts",
                "es": "Para seguimiento de entrenamientos"
            },
            "questions.reading": {
                "ru": "Чтение",
                "en": "Reading",
                "es": "Lectura"
            },
            "questions.reading_current": {
                "ru": "📖 Что читаешь?",
                "en": "📖 What are you reading?",
                "es": "📖 ¿Qué estás leyendo?"
            },
            "questions.reading_description": {
                "ru": "Для отслеживания прочитанного",
                "en": "For tracking reading",
                "es": "Para seguimiento de lectura"
            },
            "questions.creativity": {
                "ru": "Творчество",
                "en": "Creativity",
                "es": "Creatividad"
            },
            "questions.creativity_current": {
                "ru": "🎨 Чем занимаешься творчески?",
                "en": "🎨 What creative activities are you doing?",
                "es": "🎨 ¿Qué actividades creativas estás haciendo?"
            },
            "questions.creativity_description": {
                "ru": "Для развития креативности",
                "en": "For creativity development",
                "es": "Para desarrollo de creatividad"
            },
            "questions.relationships": {
                "ru": "Отношения",
                "en": "Relationships",
                "es": "Relaciones"
            },
            "questions.relationships_current": {
                "ru": "💕 Как дела с близкими?",
                "en": "💕 How are things with loved ones?",
                "es": "💕 ¿Cómo están las cosas con los seres queridos?"
            },
            "questions.relationships_description": {
                "ru": "Для укрепления отношений",
                "en": "For strengthening relationships",
                "es": "Para fortalecer relaciones"
            },
            "questions.rest": {
                "ru": "Отдых",
                "en": "Rest",
                "es": "Descanso"
            },
            "questions.rest_current": {
                "ru": "🏖️ Как отдыхаешь?",
                "en": "🏖️ How are you resting?",
                "es": "🏖️ ¿Cómo estás descansando?"
            },
            "questions.rest_description": {
                "ru": "Для баланса работы и отдыха",
                "en": "For work-life balance",
                "es": "Para equilibrio trabajo-vida"
            },
            "questions.self_development": {
                "ru": "Саморазвитие",
                "en": "Self-development",
                "es": "Autodesarrollo"
            },
            "questions.self_development_current": {
                "ru": "🌱 Над чем работаешь в себе?",
                "en": "🌱 What are you working on in yourself?",
                "es": "🌱 ¿En qué estás trabajando en ti mismo?"
            },
            "questions.self_development_description": {
                "ru": "Для личностного роста",
                "en": "For personal growth",
                "es": "Para crecimiento personal"
            },
        }
    
    def add_translations_to_files(self):
        """Добавляет все переводы в файлы локализации."""
        locale_dir = Path('bot/i18n/locales')
        
        for lang in ['ru', 'en', 'es']:
            locale_file = locale_dir / f'{lang}.json'
            
            if not locale_file.exists():
                continue
                
            with open(locale_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Добавляем новые ключи
            for key, translations in self.translation_keys.items():
                if lang in translations:
                    # Разбиваем ключ на части для nested структуры
                    parts = key.split('.')
                    current = data
                    
                    # Создаем nested структуру если нужно
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    
                    # Добавляем значение
                    current[parts[-1]] = translations[lang]
            
            # Сохраняем файл
            with open(locale_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Добавлено {len(self.translation_keys)} ключей переводов")
    
    def fix_file(self, file_path: Path) -> int:
        """Исправляет хардкод в одном файле."""
        if not file_path.exists():
            return 0
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_count = 0
        
        # Применяем замены
        for hardcode, translation_key in self.hardcode_mapping.items():
            # Различные варианты замены
            patterns = [
                # f-строки
                (rf'f"[^"]*{re.escape(hardcode)}[^"]*"', lambda m: m.group(0).replace(hardcode, f'{{translator.translate("{translation_key}")}}')),
                (rf"f'[^']*{re.escape(hardcode)}[^']*'", lambda m: m.group(0).replace(hardcode, f'{{translator.translate("{translation_key}")}}')),
                # Обычные строки
                (rf'"{re.escape(hardcode)}"', f'translator.translate("{translation_key}")'),
                (rf"'{re.escape(hardcode)}'", f'translator.translate("{translation_key}")'),
                # В InlineKeyboardButton
                (rf'InlineKeyboardButton\("([^"]*{re.escape(hardcode)}[^"]*)"', lambda m: f'InlineKeyboardButton(translator.translate("{translation_key}")'),
                (rf"InlineKeyboardButton\('([^']*{re.escape(hardcode)}[^']*)'", lambda m: f"InlineKeyboardButton(translator.translate('{translation_key}')"),
            ]
            
            for pattern, replacement in patterns:
                if re.search(pattern, content):
                    if callable(replacement):
                        content = re.sub(pattern, replacement, content)
                    else:
                        content = re.sub(pattern, replacement, content)
                    fixes_count += 1
        
        # Сохраняем файл если были изменения
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Исправлено {fixes_count} проблем в {file_path}")
        
        return fixes_count
    
    def fix_all_files(self):
        """Исправляет все файлы."""
        # Файлы для исправления
        patterns = [
            'bot/handlers/**/*.py',
            'bot/keyboards/**/*.py',
            'bot/utils/**/*.py',
            'bot/services/**/*.py',
            'bot/database/**/*.py',
            'bot/admin/**/*.py',
            'bot/cache/**/*.py',
            'bot/questions/**/*.py',
            'bot/feedback/**/*.py',
            'bot/i18n/**/*.py',
        ]
        
        total_fixes = 0
        
        for pattern in patterns:
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    fixes = self.fix_file(file_path)
                    total_fixes += fixes
        
        return total_fixes

def main():
    """Главная функция."""
    fixer = ComprehensiveHardcodeFixer()
    
    print("🔧 Начинаю ПОЛНОЕ исправление хардкода...")
    
    # Добавляем переводы
    fixer.add_translations_to_files()
    
    # Исправляем файлы
    total_fixes = fixer.fix_all_files()
    
    print(f"\n✅ Исправление завершено! Всего исправлено: {total_fixes} проблем")
    
    # Проверяем результат
    print("\n🧪 Проверяю результат...")
    os.system("python3 -m pytest tests/test_no_hardcoded_text.py::TestNoHardcodedText::test_no_hardcoded_russian_text_in_handlers -v")

if __name__ == "__main__":
    main()