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


def get_stat():
    cfg = ConfigParser()
    cfg.read(f'{sys.path[0]}/config')
    data_dir = cfg.get('data', 'path')
    devs_count = None
    intf_count = 0
    try:
        all_devices = os.listdir(data_dir)  # Все папки
        devs_count = len(all_devices)
        for device in all_devices:
            if os.path.exists(f'{data_dir}/{device}/interfaces.yaml'):
                intf_count += 1
    except Exception:
        pass
    return devs_count, intf_count


def find_description(finding_string: str, re_string: str, stop_on: str):
    print(re_string)
    cfg = ConfigParser()
    cfg.read(f'{sys.path[0]}/config')
    data_dir = cfg.get('data', 'path')

    result = []

    try:
        all_devices = sorted(os.listdir(data_dir))  # Все папки
        # Создаем упорядоченный список папок, которые необходимо сканировать
        # начиная после последнего найденного устройства, если таковое было передано
        device_to_scan = all_devices[all_devices.index(stop_on) + 1 if stop_on else 0:]

        # Производим поочередный поиск
        for device in device_to_scan:
            device = device.replace(' ', '\\ ').replace('|', '\|')
            if os.path.exists(f'{data_dir}/{device}/interfaces.yaml'):
                with open(f'{data_dir}/{device}/interfaces.yaml', 'r') as intf_yaml:
                    interfaces = yaml.safe_load(intf_yaml)
                for line in interfaces['data']:

                    if (finding_string and finding_string.lower() in line['Description'].lower()) or \
                            (re_string and len(findall(re_string, line['Description'])) != 0):
                        # Если нашли совпадение в строке
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

                        result.append({
                                'Device': device,
                                'Interface': line['Interface'],
                                'Description': line['Description'],
                                'SavedTime': saved_date,
                                'percent': f'{str(all_devices.index(device) * 100 / len(all_devices))[:5]}%'
                            })
                if result:
                    return result  # Если на данном оборудовании были найдены совпадения, то
                            # возвращаем их и прерываем дальнейший поиск

    except Exception:
        pass
    return result
