'use client'

import { useEffect, useState } from 'react'
import { supabase, type ActivityRecord } from '@/lib/supabase'
import { getTelegramUserId, initTelegramWebApp } from '@/lib/telegram'

export default function HistoryPage() {
  const [activities, setActivities] = useState<ActivityRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateFilter, setDateFilter] = useState<string>('week')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [telegramUserId, setTelegramUserId] = useState<number | null>(null)

  useEffect(() => {
    // Инициализируем Telegram Web App
    initTelegramWebApp();
    
    // Получаем ID пользователя
    const userId = getTelegramUserId();
    setTelegramUserId(userId);
    
    if (!userId) {
      setError('Не удалось получить данные пользователя Telegram');
      setLoading(false);
      return;
    }

    fetchActivities(userId);
  }, [dateFilter]);

  const fetchActivities = async (userId: number) => {
    try {
      setLoading(true);
      
      // Get user's Telegram username for filtering
      const { data: userData } = await supabase
        .from('users')
        .select('tg_username, tg_first_name, tg_last_name')
        .eq('tg_id', userId)
        .single();

      if (!userData) {
        setError('Пользователь не найден в базе данных');
        return;
      }

      const userName = userData.tg_username || 
                      `${userData.tg_first_name || ''} ${userData.tg_last_name || ''}`.trim();

      if (!userName) {
        setError('Не удалось определить имя пользователя');
        return;
      }

      // Calculate date range
      const now = new Date();
      let startDate = new Date();
      
      switch (dateFilter) {
        case 'today':
          startDate.setHours(0, 0, 0, 0);
          break;
        case 'week':
          startDate.setDate(now.getDate() - 7);
          break;
        case 'month':
          startDate.setMonth(now.getMonth() - 1);
          break;
        case 'all':
        default:
          startDate = new Date('2020-01-01');
          break;
      }

      const { data, error } = await supabase
        .from('tg_jobs')
        .select('*')
        .eq('tg_name', userName)
        .gte('jobs_timestamp', startDate.toISOString())
        .order('jobs_timestamp', { ascending: false });

      if (error) throw error;

      setActivities(data || []);
    } catch (err) {
      console.error('Error fetching activities:', err);
      setError('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const filteredActivities = activities.filter(activity =>
    activity.job_text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('ru-RU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Загрузка истории...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-100 flex items-center justify-center">
        <div className="text-center p-6">
          <div className="text-red-600 text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-red-800 mb-2">Ошибка</h1>
          <p className="text-red-600 mb-4">{error}</p>
          <p className="text-sm text-gray-600">
            Telegram User ID: {telegramUserId || 'не определен'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">📊 История активностей</h1>
          <p className="text-gray-600">Всего записей: {filteredActivities.length}</p>
          <p className="text-sm text-gray-500">ID: {telegramUserId}</p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Date Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Период
              </label>
              <select
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="today">Сегодня</option>
                <option value="week">Неделя</option>
                <option value="month">Месяц</option>
                <option value="all">Все время</option>
              </select>
            </div>

            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Поиск
              </label>
              <input
                type="text"
                placeholder="Поиск по тексту..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Activities List */}
        <div className="space-y-4">
          {filteredActivities.length === 0 ? (
            <div className="bg-white rounded-lg shadow-lg p-8 text-center">
              <div className="text-gray-400 text-6xl mb-4">📝</div>
              <h3 className="text-xl font-semibold text-gray-600 mb-2">Записей не найдено</h3>
              <p className="text-gray-500">Попробуйте изменить фильтры или период</p>
            </div>
          ) : (
            filteredActivities.map((activity) => (
              <div key={activity.job_uid} className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow">
                <div className="flex justify-between items-start mb-3">
                  <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
                    {formatDate(activity.jobs_timestamp)}
                  </span>
                </div>
                <p className="text-gray-800 text-lg leading-relaxed">
                  {activity.job_text}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Stats Footer */}
        {filteredActivities.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg p-6 mt-6">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">📈 Статистика</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{filteredActivities.length}</div>
                <div className="text-sm text-gray-600">Записей</div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {Math.round(filteredActivities.reduce((acc, a) => acc + a.job_text.length, 0) / filteredActivities.length) || 0}
                </div>
                <div className="text-sm text-gray-600">Ср. длина</div>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">
                  {new Set(filteredActivities.map(a => a.jobs_timestamp.split('T')[0])).size}
                </div>
                <div className="text-sm text-gray-600">Дней</div>
              </div>
              <div className="bg-orange-50 p-4 rounded-lg">
                <div className="text-2xl font-bold text-orange-600">
                  {filteredActivities.reduce((acc, a) => acc + a.job_text.split(' ').length, 0)}
                </div>
                <div className="text-sm text-gray-600">Слов</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}