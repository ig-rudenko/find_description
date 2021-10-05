import os
import sys
import yaml
from re import findall, sub
from configparser import ConfigParser
from dateconverter import DateConverter
from datetime import date, timedelta


def get_stat(st: str):
    cfg = ConfigParser()
    cfg.read(f'{sys.path[0]}/config')
    data_dir = cfg.get('data', 'path')
    devs_count = None
    intf_count = 0
    try:
        all_devices = os.listdir(data_dir)  # Все папки
        devs_count = len(all_devices)
        for device in all_devices:
            if os.path.exists(f'{data_dir}/{device}/{st}.yaml'):
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


def reformatting(name: str):
    with open(f'{sys.path[0]}/vlan_traceroute/name_format.yaml') as file:
        name_format = yaml.safe_load(file)

    for n in name_format:
        if n == name:  # Если имя совпадает с правильным, то отправляем его
            return name
        for pattern in name_format[n]:
            if pattern in name:  # Если паттерн содержится в исходном имени
                return sub(pattern, n, name)  # Заменяем совпадение "pattern" в названии "name" на правильное "n"
    return name


def vlan_range(vlans_ranges: list) -> set:
    """
    Преобразовывает сокращенные диапазоны VLAN'ов в развернутый список

    14, 100-103, 142 -> 14, 100, 101, 102, 103, 142

    :param vlans_ranges: Список диапазонов
    :return: развернутое множество VLAN'ов
    """
    vlans = []
    for v_range in vlans_ranges:
        if len(v_range.split()) > 1:
            vlans += list(vlan_range(v_range.split()))
        try:
            if '-' in v_range:
                parts = v_range.split('-')
                vlans += range(int(parts[0]), int(parts[1])+1)
            else:
                vlans.append(int(v_range))
        except ValueError:
            pass

    return set(vlans)


cfg = ConfigParser()
cfg.read(f'{sys.path[0]}/config')
data_dir = cfg.get('data', 'path')


def find_vlan(device: str, vlan_to_find: int, passed_devices: set, dict_enter: dict, result: list):
    """
        Осуществляет поиск VLAN'ов по портам оборудования, которое расположено в папке /root_dir/data/device/
        И имеет файл vlans.yaml
        :param device: Имя устройства, на котором осуществляется поиск
        :param vlan_to_find: VLAN, который ищем
        :param passed_devices:  Уже пройденные устройства
        :param dict_enter:  Вхождение
        """

    dict_enter[device] = {}

    passed_devices.add(device)  # Добавляем узел в список уже пройденных устройств
    if not os.path.exists(os.path.join(data_dir, device, 'vlans.yaml')):
        return
    with open(os.path.join(data_dir, device, 'vlans.yaml')) as file_yaml:
        vlans_yaml = yaml.safe_load(file_yaml)

    interfaces = vlans_yaml['data']
    if not interfaces:
        return

    intf_found_count = 0  # Кол-во найденных интерфейсов на этом устройстве

    for line in interfaces:

        vlans_list = []  # Список VLAN'ов на порту
        if 'all' in line["VLAN's"]:
            # Если разрешено пропускать все вланы
            vlans_list = list(range(1, 4097))
        else:
            if 'to' in line["VLAN's"]:
                # Если имеется формат "trunk,1 to 7 12 to 44"
                vv = [list(range(int(v[0]), int(v[1]) + 1)) for v in
                      [range_ for range_ in findall(r'(\d+)\s*to\s*(\d+)', line["VLAN's"])]]
                for v in vv:
                    vlans_list += v
            else:
                # Формат представления стандартный "trunk,123,33,10-100"
                vlans_list = vlan_range([v for v in line["VLAN's"].split(',') if
                                         v != 'trunk' and v != 'access' and v != 'hybrid' and v != 'dot1q-tunnel'])
                # Если искомый vlan находится в списке vlan'ов на данном интерфейсе
        if vlan_to_find in vlans_list:

            intf_found_count += 1

            dict_enter[device][line["Interface"] + ' --- ' + line["Description"]] = {}

            next_device = findall(r'SVSL\S+SW\d+', line["Description"])  # Ищем в описании порта следующий узел сети
            # Приводим к единому формату имя узла сети
            next_device = reformatting(next_device[0]) if next_device else ''

            # Создаем данные для visual
            if next_device:
                result.append(
                    (device, next_device, 10, line["Interface"] + ' --- ' + line["Description"])
                )

            if next_device and next_device not in list(passed_devices):
                find_vlan(
                    next_device,
                    vlan_to_find,
                    passed_devices,
                    dict_enter=dict_enter[device][line["Interface"] + ' --- ' + line["Description"]],
                    result=result
                )
