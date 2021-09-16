import os
import sys
import yaml
from re import findall
from configparser import ConfigParser
from dateconverter import DateConverter
from datetime import date, timedelta


def admin_status_color(admin_status: str) -> str:
    if findall(r'down|DOWN|\*|Dis', admin_status):
        return f'\x1b[5;41m{admin_status}\x1b[0m'
    else:
        return f'\x1b[1;32m{admin_status}\x1b[0m'


def find_description(find_str: list, find_re: list, stop_on: str):
    cfg = ConfigParser()
    cfg.read(f'{sys.path[0]}/config')
    data_dir = cfg.get('data', 'path')

    result = {}
    finding_string = '|'.join(find_str).lower()

    re_string = '|'.join(find_re)

    try:
        all_devices = sorted(os.listdir(data_dir))  # Все папки
        # Создаем упорядоченный список папок, которые необходимо сканировать
        # начиная после последнего найденного устройства, если таковое было передано
        device_to_scan = all_devices[all_devices.index(stop_on) + 1 if stop_on else 0:]
        print(device_to_scan)

        # Производим поочередный поиск
        for device in device_to_scan:
            if os.path.exists(f'{data_dir}/{device}/interfaces.yaml'):
                with open(f'{data_dir}/{device}/interfaces.yaml', 'r') as intf_yaml:
                    interfaces = yaml.safe_load(intf_yaml)
                for line in interfaces['data']:
                    if (findall(finding_string, line['Description'].lower()) and find_str) or \
                            (findall(re_string, line['Description']) and find_re):
                        # Если нашли совпадение в строке
                        # Возвращаем первое найденное
                        if interfaces.get('saved time') and \
                                DateConverter(interfaces.get('saved time')).date == date.today():
                            saved_date = f'Сегодня в {interfaces["saved time"].split(",")[1].strip()}'

                        elif interfaces.get('saved time') and \
                                DateConverter(interfaces.get('saved time')).date == date.today()-timedelta(days=1):
                            saved_date = f'Вчера в {interfaces["saved time"].split(",")[1].strip()}'

                        elif interfaces.get('saved time') and \
                                DateConverter(interfaces.get('saved time')).date == date.today()-timedelta(days=2):
                            saved_date = f'Позавчера в {interfaces["saved time"].split(",")[1].strip()}'

                        elif interfaces.get('saved time'):
                            saved_date = f'{DateConverter(interfaces["saved time"])} ' + \
                                         interfaces["saved time"].split(",")[1].strip()
                        else:
                            saved_date = ''

                        return {
                                'Device': device,
                                'Interface': line['Interface'],
                                'Description': line['Description'],
                                'SavedTime': saved_date
                            }

    except Exception:
        pass
    return result
