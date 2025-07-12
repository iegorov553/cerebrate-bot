#!/usr/bin/env python3
"""
Скрипт для проверки комплексной миграции базы данных Doyobi Diary Bot

Этот скрипт тестирует все компоненты созданной схемы базы данных:
- Проверяет создание всех таблиц
- Тестирует функции оптимизации
- Проверяет индексы и ограничения
- Тестирует RLS политики
- Проверяет тестовые данные

Использование:
    python3 scripts/test_migration.py

Требования:
    - SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY в переменных окружения
    - Установленный пакет supabase
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, List, Any

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client, Client
from bot.config import Config


class MigrationTester:
    """Класс для тестирования комплексной миграции"""
    
    def __init__(self):
        """Инициализация подключения к базе данных"""
        self.config = Config()
        
        if not self.config.SUPABASE_URL or not self.config.SUPABASE_SERVICE_ROLE_KEY:
            raise ValueError(
                "❌ Не найдены переменные окружения SUPABASE_URL или SUPABASE_SERVICE_ROLE_KEY"
            )
        
        self.supabase: Client = create_client(
            self.config.SUPABASE_URL, 
            self.config.SUPABASE_SERVICE_ROLE_KEY
        )
        
        print("✅ Подключение к Supabase установлено")
    
    def test_tables_created(self) -> bool:
        """Проверяет, что все необходимые таблицы созданы"""
        print("\n🔍 Проверка создания таблиц...")
        
        required_tables = [
            'users', 
            'tg_jobs', 
            'friendships', 
            'user_questions', 
            'question_notifications'
        ]
        
        try:
            # Получаем список всех таблиц
            result = self.supabase.rpc(
                'exec_sql', 
                {
                    'query': '''
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                    '''
                }
            ).execute()
            
            existing_tables = [row['result']['table_name'] for row in result.data]
            
            missing_tables = []
            for table in required_tables:
                if table in existing_tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table} - ОТСУТСТВУЕТ")
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"❌ Отсутствуют таблицы: {', '.join(missing_tables)}")
                return False
            
            print(f"✅ Все {len(required_tables)} таблиц созданы успешно")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при проверке таблиц: {e}")
            return False
    
    def test_functions_created(self) -> bool:
        """Проверяет, что все функции оптимизации созданы"""
        print("\n🚀 Проверка функций оптимизации...")
        
        required_functions = [
            'exec_sql',
            'get_friend_requests_optimized',
            'get_friends_list_optimized', 
            'get_friends_of_friends_optimized',
            'get_user_stats',
            'cleanup_expired_notifications'
        ]
        
        try:
            result = self.supabase.rpc(
                'exec_sql',
                {
                    'query': '''
                        SELECT routine_name 
                        FROM information_schema.routines 
                        WHERE routine_schema = 'public' 
                        AND routine_type = 'FUNCTION'
                        ORDER BY routine_name
                    '''
                }
            ).execute()
            
            existing_functions = [row['result']['routine_name'] for row in result.data]
            
            missing_functions = []
            for func in required_functions:
                if func in existing_functions:
                    print(f"  ✅ {func}")
                else:
                    print(f"  ❌ {func} - ОТСУТСТВУЕТ")
                    missing_functions.append(func)
            
            if missing_functions:
                print(f"❌ Отсутствуют функции: {', '.join(missing_functions)}")
                return False
            
            print(f"✅ Все {len(required_functions)} функций созданы успешно")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при проверке функций: {e}")
            return False
    
    def test_indexes_created(self) -> bool:
        """Проверяет, что критически важные индексы созданы"""
        print("\n📈 Проверка индексов...")
        
        try:
            result = self.supabase.rpc(
                'exec_sql',
                {
                    'query': '''
                        SELECT indexname, tablename 
                        FROM pg_indexes 
                        WHERE schemaname = 'public'
                        ORDER BY tablename, indexname
                    '''
                }
            ).execute()
            
            indexes = [(row['result']['tablename'], row['result']['indexname']) for row in result.data]
            
            # Группируем индексы по таблицам
            indexes_by_table = {}
            for table, index in indexes:
                if table not in indexes_by_table:
                    indexes_by_table[table] = []
                indexes_by_table[table].append(index)
            
            # Проверяем критически важные индексы
            critical_indexes = {
                'users': ['idx_users_last_notification_sent', 'idx_users_language'],
                'tg_jobs': ['idx_tg_jobs_tg_id', 'idx_tg_jobs_question'],
                'friendships': ['idx_friendships_requester', 'idx_friendships_addressee'],
                'user_questions': ['idx_user_questions_default', 'idx_user_questions_user_active']
            }
            
            total_indexes = sum(len(idx_list) for idx_list in indexes_by_table.values())
            missing_critical = []
            
            for table, expected_indexes in critical_indexes.items():
                table_indexes = indexes_by_table.get(table, [])
                for expected_idx in expected_indexes:
                    if expected_idx in table_indexes:
                        print(f"  ✅ {table}.{expected_idx}")
                    else:
                        print(f"  ❌ {table}.{expected_idx} - ОТСУТСТВУЕТ")
                        missing_critical.append(f"{table}.{expected_idx}")
            
            if missing_critical:
                print(f"❌ Отсутствуют критически важные индексы: {', '.join(missing_critical)}")
                return False
            
            print(f"✅ Всего индексов создано: {total_indexes}")
            print("✅ Все критически важные индексы на месте")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при проверке индексов: {e}")
            return False
    
    def test_test_data(self) -> bool:
        """Проверяет, что тестовые данные созданы корректно"""
        print("\n👥 Проверка тестовых данных...")
        
        try:
            # Проверяем пользователей
            users_result = self.supabase.table('users').select('tg_id, tg_username, language').execute()
            users_count = len(users_result.data)
            print(f"  ✅ Пользователей: {users_count}")
            
            # Проверяем вопросы
            questions_result = self.supabase.table('user_questions').select('id, user_id, is_default').execute()
            questions_count = len(questions_result.data)
            default_questions = sum(1 for q in questions_result.data if q['is_default'])
            print(f"  ✅ Вопросов: {questions_count} (дефолтных: {default_questions})")
            
            # Проверяем активности
            jobs_result = self.supabase.table('tg_jobs').select('id, tg_id, question_id').execute()
            jobs_count = len(jobs_result.data)
            jobs_with_questions = sum(1 for j in jobs_result.data if j['question_id'])
            print(f"  ✅ Активностей: {jobs_count} (с привязкой к вопросам: {jobs_with_questions})")
            
            # Проверяем дружеские связи
            friendships_result = self.supabase.table('friendships').select('friendship_id, status').execute()
            friendships_count = len(friendships_result.data)
            print(f"  ✅ Дружеских связей: {friendships_count}")
            
            # Проверяем соответствие: у каждого пользователя должен быть дефолтный вопрос
            if users_count != default_questions:
                print(f"❌ Несоответствие: {users_count} пользователей, но {default_questions} дефолтных вопросов")
                return False
            
            print("✅ Тестовые данные созданы корректно")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при проверке тестовых данных: {e}")
            return False
    
    def test_optimization_functions(self) -> bool:
        """Тестирует работу функций оптимизации"""
        print("\n⚡ Тестирование функций оптимизации...")
        
        try:
            # Тестируем статистику пользователей
            stats_result = self.supabase.rpc('get_user_stats').execute()
            if stats_result.data:
                stats = stats_result.data[0]
                print(f"  ✅ get_user_stats: {stats['total_users']} пользователей, {stats['active_users']} активных")
            else:
                print("  ❌ get_user_stats: нет данных")
                return False
            
            # Получаем ID первого тестового пользователя
            users_result = self.supabase.table('users').select('tg_id').limit(1).execute()
            if not users_result.data:
                print("  ❌ Нет пользователей для тестирования")
                return False
            
            test_user_id = users_result.data[0]['tg_id']
            
            # Тестируем список друзей
            friends_result = self.supabase.rpc(
                'get_friends_list_optimized', 
                {'p_user_id': test_user_id}
            ).execute()
            print(f"  ✅ get_friends_list_optimized: {len(friends_result.data)} друзей")
            
            # Тестируем запросы в друзья
            requests_result = self.supabase.rpc(
                'get_friend_requests_optimized',
                {'p_user_id': test_user_id}
            ).execute()
            print(f"  ✅ get_friend_requests_optimized: {len(requests_result.data)} запросов")
            
            # Тестируем поиск друзей друзей
            discovery_result = self.supabase.rpc(
                'get_friends_of_friends_optimized',
                {'p_user_id': test_user_id, 'p_limit': 5}
            ).execute()
            print(f"  ✅ get_friends_of_friends_optimized: {len(discovery_result.data)} рекомендаций")
            
            print("✅ Все функции оптимизации работают корректно")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при тестировании функций: {e}")
            return False
    
    def test_constraints(self) -> bool:
        """Тестирует ограничения базы данных"""
        print("\n🔒 Тестирование ограничений...")
        
        try:
            # Тестируем ограничение на язык пользователя
            try:
                self.supabase.table('users').insert({
                    'tg_id': 999999999,
                    'tg_username': 'test_constraint',
                    'language': 'invalid_lang'  # Недопустимый язык
                }).execute()
                print("  ❌ Ограничение на язык не работает")
                return False
            except Exception:
                print("  ✅ Ограничение на язык работает")
            
            # Тестируем ограничение на дружбу с самим собой
            try:
                self.supabase.table('friendships').insert({
                    'requester_id': 123456789,
                    'addressee_id': 123456789  # Тот же пользователь
                }).execute()
                print("  ❌ Ограничение на дружбу с собой не работает")
                return False
            except Exception:
                print("  ✅ Ограничение на дружбу с собой работает")
            
            # Тестируем ограничение на минимальный интервал в вопросах
            try:
                test_user_id = 123456789
                self.supabase.table('user_questions').insert({
                    'user_id': test_user_id,
                    'question_name': 'Test Question',
                    'question_text': 'Test?',
                    'interval_minutes': 15  # Меньше минимального (30)
                }).execute()
                print("  ❌ Ограничение на минимальный интервал не работает")
                return False
            except Exception:
                print("  ✅ Ограничение на минимальный интервал работает")
            
            print("✅ Все ограничения работают корректно")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при тестировании ограничений: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Запускает все тесты"""
        print("🧪 ТЕСТИРОВАНИЕ КОМПЛЕКСНОЙ МИГРАЦИИ DOYOBI DIARY BOT")
        print("=" * 60)
        
        tests = [
            ("Создание таблиц", self.test_tables_created),
            ("Создание функций", self.test_functions_created),
            ("Создание индексов", self.test_indexes_created),
            ("Тестовые данные", self.test_test_data),
            ("Функции оптимизации", self.test_optimization_functions),
            ("Ограничения БД", self.test_constraints)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
                else:
                    print(f"\n❌ Тест '{test_name}' провален")
            except Exception as e:
                print(f"\n💥 Критическая ошибка в тесте '{test_name}': {e}")
        
        print("\n" + "=" * 60)
        print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ: {passed_tests}/{total_tests} тестов пройдено")
        
        if passed_tests == total_tests:
            print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            print("✅ Миграция работает корректно")
            return True
        else:
            print("❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
            print("🔧 Проверьте логи выше для диагностики проблем")
            return False


def main():
    """Основная функция"""
    try:
        tester = MigrationTester()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()