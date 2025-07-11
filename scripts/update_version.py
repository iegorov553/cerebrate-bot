#!/usr/bin/env python3
"""
Автоматически обновляет версию бота при коммите.
Увеличивает patch версию (2.1.0 -> 2.1.1) при каждом коммите.
"""

import re
from pathlib import Path

def update_version():
    """Обновляет версию в файле VERSION."""
    version_file = Path(__file__).parent.parent / "VERSION"
    
    if not version_file.exists():
        print("Файл VERSION не найден!")
        return
    
    current_version = version_file.read_text().strip()
    
    # Парсим версию (major.minor.patch)
    match = re.match(r'(\d+)\.(\d+)\.(\d+)', current_version)
    if not match:
        print(f"Неверный формат версии: {current_version}")
        return
    
    major, minor, patch = map(int, match.groups())
    
    # Увеличиваем patch версию
    new_patch = patch + 1
    new_version = f"{major}.{minor}.{new_patch}"
    
    # Записываем новую версию
    version_file.write_text(new_version)
    
    print(f"Версия обновлена: {current_version} -> {new_version}")
    return new_version

if __name__ == "__main__":
    update_version()