# test_task_playrix
Выполнение тестового задания для playrix

* Требуется python версии >=3.6
* Используются только встроенные библиотеки
* Для обращения к api github'а без ограничения в 60 запросов в час требуется авторизация. Для этого необходимо переименовать файл config.json.example в config.json и отредактировать в нём значения user/password.
* Чтобы ознакоиться с возможными аргументами:
```
python github_analyze.py --help
```
* Пример запуска:
```
python github_analize.py --url 'https://github.com/fastlane/fastlane/'
 -s 2020-01-15 -f '%Y-%m-%d' -b janpio-screengrab_adb_windows
```
