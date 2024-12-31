#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

class TodoHandler(BaseHTTPRequestHandler):
    tasks = []       # Список задач (каждая задача — словарь с ключами title, priority, isDone, id)
    next_id = 1      # Следующий свободный идентификатор
    data_file = 'tasks.txt'

    @classmethod
    def load_tasks(cls):
        """Читаем задачи из файла при старте сервера (если файл существует)."""
        if os.path.exists(cls.data_file):
            with open(cls.data_file, 'r', encoding='utf-8') as f:
                try:
                    cls.tasks = json.load(f)
                except json.JSONDecodeError:
                    cls.tasks = []
            # Чтобы при перезапуске ID продолжал считаться дальше, ищем максимальный существующий ID
            if cls.tasks:
                max_id = max(task['id'] for task in cls.tasks)
                cls.next_id = max_id + 1
            else:
                cls.next_id = 1

    @classmethod
    def save_tasks(cls):
        """Сохраняем задачи в файл."""
        with open(cls.data_file, 'w', encoding='utf-8') as f:
            json.dump(cls.tasks, f, ensure_ascii=False)

    def do_GET(self):
        """Обработка GET-запросов:
           - GET /tasks -> вернуть список всех задач
        """
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/tasks':
            # Возвращаем список задач
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            response_data = json.dumps(self.tasks, ensure_ascii=False)
            self.wfile.write(response_data.encode('utf-8'))
        else:
            # Неизвестный путь
            self.send_error(404, 'Not Found')

    def do_POST(self):
        """Обработка POST-запросов:
           1) POST /tasks c телом JSON: {"title": "...", "priority": "..."} -> создать новую задачу
           2) POST /tasks/<id>/complete -> отметить задачу как выполненную
        """
        parsed_path = urlparse(self.path)
        path_segments = list(filter(None, parsed_path.path.split('/')))

        if self.path == '/tasks':
            # Создание новой задачи
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self.send_error(400, 'Invalid JSON')
                return

            title = data.get('title')
            priority = data.get('priority')

            if not title or not priority:
                self.send_error(400, 'Missing title or priority')
                return

            new_task = {
                'id': self.__class__.next_id,
                'title': title,
                'priority': priority,
                'isDone': False
            }
            self.__class__.tasks.append(new_task)
            self.__class__.next_id += 1

            # Сохраняем в файл после изменения
            self.__class__.save_tasks()

            # Возвращаем данные о созданной задаче
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(new_task, ensure_ascii=False).encode('utf-8'))

        elif len(path_segments) == 3 and path_segments[0] == 'tasks' and path_segments[2] == 'complete':
            # Маркировка задачи как выполненной: POST /tasks/<id>/complete
            try:
                task_id = int(path_segments[1])
            except ValueError:
                self.send_error(400, 'Invalid task id')
                return

            # Ищем задачу
            task_found = False
            for task in self.__class__.tasks:
                if task['id'] == task_id:
                    task['isDone'] = True
                    task_found = True
                    break

            if task_found:
                # Сохраняем в файл
                self.__class__.save_tasks()

                # Пустой ответ, код 200
                self.send_response(200)
                self.end_headers()
            else:
                # Задача не найдена
                self.send_error(404, 'Task not found')
        else:
            # Неизвестный путь
            self.send_error(404, 'Not Found')

def run_server(host='127.0.0.1', port=8080):
    """Запуск сервера."""
    TodoHandler.load_tasks()  # Перед стартом сервера загрузим уже имеющиеся задачи из файла
    server_address = (host, port)
    httpd = HTTPServer(server_address, TodoHandler)
    print(f'Сервер запущен на http://{host}:{port}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nОстановка сервера...')
    httpd.server_close()

if __name__ == '__main__':
    run_server()

