"""
Question templates for quick question creation.

This module provides predefined question templates organized by categories.
"""

from typing import Dict, List


class QuestionTemplates:
    """Predefined question templates for users."""

    @staticmethod
    def get_templates() -> Dict[str, List[Dict]]:
        """
        Get all question templates organized by categories.

        Returns:
            Dictionary with categories and their templates
        """
        return {
            "work_study": [
                {
                    "name": translator.translate("questions.work_tasks"),
                    "text": translator.translate("questions.work_current"),
                    "window_start": "09:00",
                    "window_end": "18:00",
                    "interval_minutes": 180,  # 3 hours
                    "description": translator.translate("questions.work_description")
                },
                {
                    "name": translator.translate("questions.learning"),
                    "text": translator.translate("questions.learning_current"),
                    "window_start": "10:00",
                    "window_end": "22:00",
                    "interval_minutes": 240,  # 4 hours
                    "description": translator.translate("questions.learning_description")
                },
                {
                    "name": translator.translate("questions.daily_goals"),
                    "text": "🎯 Какие задачи решаешь?",
                    "window_start": "09:00",
                    "window_end": "19:00",
                    "interval_minutes": 300,  # 5 hours
                    "description": "Контроль выполнения ежедневных целей"
                }
            ],
            "personal": [
                {
                    "name": "Настроение",
                    "text": "😊 Как настроение?",
                    "window_start": "10:00",
                    "window_end": "20:00",
                    "interval_minutes": 360,  # 6 hours
                    "description": translator.translate("questions.emotions_description")
                },
                {
                    "name": translator.translate("questions.sport"),
                    "text": "💪 Как дела со спортом?",
                    "window_start": "07:00",
                    "window_end": "21:00",
                    "interval_minutes": 720,  # 12 hours
                    "description": "Контроль физической активности"
                },
                {
                    "name": "Достижения",
                    "text": "🌟 Что хорошего произошло?",
                    "window_start": "12:00",
                    "window_end": "22:00",
                    "interval_minutes": 480,  # 8 hours
                    "description": "Фиксация позитивных моментов"
                }
            ],
            "time_based": [
                {
                    "name": translator.translate("questions.morning_checkin"),
                    "text": "🌅 Доброе утро! Как планы на день?",
                    "window_start": "07:00",
                    "window_end": "10:00",
                    "interval_minutes": 1440,  # 24 hours (once a day)
                    "description": "Ежедневная утренняя проверка"
                },
                {
                    "name": "Обеденный перерыв",
                    "text": "🍽️ Как обед? Что дальше планируешь?",
                    "window_start": "12:00",
                    "window_end": "14:00",
                    "interval_minutes": 1440,  # 24 hours
                    "description": "Проверка в середине дня"
                },
                {
                    "name": "Вечерний отчёт",
                    "text": translator.translate("questions.main_question"),
                    "window_start": "19:00",
                    "window_end": "22:00",
                    "interval_minutes": 1440,  # 24 hours
                    "description": "Ежедневное подведение итогов"
                }
            ],
            "health": [
                {
                    "name": translator.translate("questions.health"),
                    "text": "🏥 Как самочувствие?",
                    "window_start": "09:00",
                    "window_end": "21:00",
                    "interval_minutes": 720,  # 12 hours
                    "description": "Контроль состояния здоровья"
                },
                {
                    "name": "Питание",
                    "text": "🥗 Что ел полезного?",
                    "window_start": "12:00",
                    "window_end": "20:00",
                    "interval_minutes": 480,  # 8 hours
                    "description": "Отслеживание правильного питания"
                },
                {
                    "name": "Сон",
                    "text": "😴 Как спалось? Как самочувствие?",
                    "window_start": "08:00",
                    "window_end": "11:00",
                    "interval_minutes": 1440,  # 24 hours
                    "description": "Контроль качества сна"
                }
            ]
        }

    @staticmethod
    def get_category_names() -> Dict[str, str]:
        """
        Get localized category names.

        Returns:
            Dictionary mapping category keys to display names
        """
        return {
            "work_study": "💼 Работа и учёба",
            "personal": "🌟 Личное развитие",
            "time_based": "⏰ По времени суток",
            "health": "💪 Здоровье"
        }

    @staticmethod
    def get_template_by_name(name: str) -> Dict:
        """
        Get template by name.

        Args:
            name: Template name

        Returns:
            Template dictionary or None if not found
        """
        templates = QuestionTemplates.get_templates()

        for category_templates in templates.values():
            for template in category_templates:
                if template["name"] == name:
                    return template

        return None

    @staticmethod
    def search_templates(query: str) -> List[Dict]:
        """
        Search templates by query.

        Args:
            query: Search query

        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        templates = QuestionTemplates.get_templates()
        results = []

        for category_templates in templates.values():
            for template in category_templates:
                if (query_lower in template["name"].lower()
                    or query_lower in template["text"].lower()
                        or query_lower in template["description"].lower()):
                    results.append(template)

        return results

    @staticmethod
    def get_popular_templates() -> List[Dict]:
        """
        Get most popular/recommended templates.

        Returns:
            List of popular templates
        """
        popular_names = [
            translator.translate("questions.work_tasks"),
            "Настроение",
            translator.translate("questions.morning_checkin"),
            "Вечерний отчёт",
            translator.translate("questions.learning")
        ]

        popular = []
        for name in popular_names:
            template = QuestionTemplates.get_template_by_name(name)
            if template:
                popular.append(template)

        return popular

    @staticmethod
    def customize_template(template: Dict, customizations: Dict) -> Dict:
        """
        Customize template with user preferences.

        Args:
            template: Base template
            customizations: User customizations

        Returns:
            Customized template
        """
        customized = template.copy()

        # Apply customizations
        for key, value in customizations.items():
            if key in customized and value is not None:
                customized[key] = value

        # Ensure required fields
        if "interval_minutes" in customized:
            customized["interval_minutes"] = max(30, customized["interval_minutes"])

        return customized
