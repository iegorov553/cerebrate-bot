// Функции для работы с Telegram Web App
// Используем более старую стабильную версию SDK

export function getTelegramUserId(): number | null {
  try {
    // Проверяем глобальный объект Telegram Web App
    if (typeof window !== 'undefined' && (window as any).Telegram?.WebApp?.initDataUnsafe?.user?.id) {
      return (window as any).Telegram.WebApp.initDataUnsafe.user.id;
    }
    
    // Fallback: пытаемся извлечь из URL параметров
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const userId = urlParams.get('user_id');
      if (userId) {
        return parseInt(userId, 10);
      }
    }
    
    return null;
  } catch (error) {
    console.error('Failed to get Telegram user ID:', error);
    return null;
  }
}

export function getTelegramUserInfo() {
  try {
    if (typeof window !== 'undefined' && (window as any).Telegram?.WebApp?.initDataUnsafe?.user) {
      const user = (window as any).Telegram.WebApp.initDataUnsafe.user;
      return {
        id: user.id,
        username: user.username,
        firstName: user.first_name,
        lastName: user.last_name,
      };
    }
    
    // Fallback: используем URL параметры
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      return {
        id: urlParams.get('user_id') ? parseInt(urlParams.get('user_id')!, 10) : null,
        username: urlParams.get('username'),
        firstName: urlParams.get('first_name'),
        lastName: urlParams.get('last_name'),
      };
    }
    
    return null;
  } catch (error) {
    console.error('Failed to get Telegram user info:', error);
    return null;
  }
}

// Инициализация Telegram Web App
export function initTelegramWebApp() {
  try {
    if (typeof window !== 'undefined' && (window as any).Telegram?.WebApp) {
      (window as any).Telegram.WebApp.ready();
      return true;
    }
    return false;
  } catch (error) {
    console.error('Failed to initialize Telegram Web App:', error);
    return false;
  }
}