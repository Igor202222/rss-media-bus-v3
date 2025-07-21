#!/usr/bin/env python3
"""
RSS Media Bus Manager v3.0
Управление RSS Bus Core и User Notification Service
"""

import subprocess
import time
import signal
import sys
from pathlib import Path

class RSSBusManager:
    def __init__(self):
        self.rss_core_process = None
        self.notification_service_process = None
        self.running = False
    
    def start_rss_core(self):
        """Запуск RSS Bus Core"""
        try:
            print("🚌 Запускаю RSS Bus Core...")
            self.rss_core_process = subprocess.Popen([
                'python3', 'rss_bus_core.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            print(f"✅ RSS Bus Core запущен (PID: {self.rss_core_process.pid})")
            return True
        except Exception as e:
            print(f"❌ Ошибка запуска RSS Bus Core: {e}")
            return False
    
    def start_notification_service(self):
        """Запуск User Notification Service"""
        try:
            print("🔔 Запускаю User Notification Service...")
            self.notification_service_process = subprocess.Popen([
                'python3', 'user_notification_service.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            print(f"✅ User Notification Service запущен (PID: {self.notification_service_process.pid})")
            return True
        except Exception as e:
            print(f"❌ Ошибка запуска User Notification Service: {e}")
            return False
    
    def check_processes(self):
        """Проверка состояния процессов"""
        rss_core_alive = self.rss_core_process and self.rss_core_process.poll() is None
        notification_alive = self.notification_service_process and self.notification_service_process.poll() is None
        
        return rss_core_alive, notification_alive
    
    def show_status(self):
        """Показать статус всех процессов"""
        rss_core_alive, notification_alive = self.check_processes()
        
        print("\n📊 Статус RSS Media Bus:")
        print("=" * 40)
        
        if rss_core_alive:
            print(f"🚌 RSS Bus Core: ✅ работает (PID: {self.rss_core_process.pid})")
        else:
            print("🚌 RSS Bus Core: ❌ остановлен")
        
        if notification_alive:
            print(f"🔔 User Notification Service: ✅ работает (PID: {self.notification_service_process.pid})")
        else:
            print("🔔 User Notification Service: ❌ остановлен")
        
        return rss_core_alive and notification_alive
    
    def restart_failed_processes(self):
        """Перезапуск упавших процессов"""
        rss_core_alive, notification_alive = self.check_processes()
        
        if not rss_core_alive and self.rss_core_process:
            print("⚠️ RSS Bus Core упал, перезапускаю...")
            self.start_rss_core()
        
        if not notification_alive and self.notification_service_process:
            print("⚠️ User Notification Service упал, перезапускаю...")
            self.start_notification_service()
    
    def stop_all(self):
        """Остановка всех процессов"""
        print("\n🛑 Останавливаю все процессы...")
        
        if self.rss_core_process:
            try:
                self.rss_core_process.terminate()
                self.rss_core_process.wait(timeout=10)
                print("✅ RSS Bus Core остановлен")
            except subprocess.TimeoutExpired:
                self.rss_core_process.kill()
                print("🔥 RSS Bus Core принудительно завершен")
            except Exception as e:
                print(f"⚠️ Ошибка остановки RSS Bus Core: {e}")
        
        if self.notification_service_process:
            try:
                self.notification_service_process.terminate()
                self.notification_service_process.wait(timeout=10)
                print("✅ User Notification Service остановлен")
            except subprocess.TimeoutExpired:
                self.notification_service_process.kill()
                print("🔥 User Notification Service принудительно завершен")
            except Exception as e:
                print(f"⚠️ Ошибка остановки User Notification Service: {e}")
        
        self.running = False
    
    def signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения"""
        print(f"\n🛑 Получен сигнал {signum}")
        self.stop_all()
        sys.exit(0)
    
    def start_all(self):
        """Запуск всей системы RSS Media Bus"""
        print("🚀 RSS Media Bus Manager v3.0")
        print("=" * 50)
        
        # Устанавливаем обработчики сигналов
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Запускаем RSS Bus Core
        if not self.start_rss_core():
            print("❌ Не удалось запустить RSS Bus Core")
            return False
        
        # Ждем немного для инициализации
        print("⏳ Ожидание инициализации RSS Bus Core...")
        time.sleep(5)
        
        # Запускаем User Notification Service
        if not self.start_notification_service():
            print("❌ Не удалось запустить User Notification Service")
            self.stop_all()
            return False
        
        print("\n🎉 RSS Media Bus полностью запущен!")
        self.show_status()
        
        self.running = True
        return True
    
    def monitor_loop(self):
        """Основной цикл мониторинга"""
        print("\n🔄 Начинаю мониторинг процессов...")
        print("📝 Для остановки нажмите Ctrl+C")
        
        try:
            while self.running:
                time.sleep(30)  # Проверяем каждые 30 секунд
                
                if not self.show_status():
                    print("⚠️ Обнаружены упавшие процессы")
                    self.restart_failed_processes()
                
        except KeyboardInterrupt:
            print("\n🛑 Получен сигнал остановки от пользователя")
            self.stop_all()

def main():
    manager = RSSBusManager()
    
    if manager.start_all():
        manager.monitor_loop()
    
    print("👋 RSS Media Bus Manager завершен")

if __name__ == "__main__":
    main() 