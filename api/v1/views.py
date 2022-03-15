from rest_framework.views import APIView
from rest_framework.response import Response

from configparser import ConfigParser
import yaml
import sys
import os


def auth_check(requests):
    """
    Проверяет API key
    """
    # Проверяем, передан ли в заголовку ключ API
    if not requests.META.get('HTTP_API_KEY'):
        return {'error': 'Not Authorized'}, 401  # Не авторизирован
    cfg = ConfigParser()
    cfg.read(f'{sys.path[0]}/config')
    api_key = cfg.get('api', 'key')
    if api_key != requests.META['HTTP_API_KEY']:
        return {'error': 'Invalid API key'}, 400
    return None, 200


def get_dat_gir():
    """
    Возвращает полный путь до папки с данными
    """
    cfg = ConfigParser()
    cfg.read(f'{sys.path[0]}/config')
    return cfg.get('data', 'path')


class GetStatInfo(APIView):
    """
    Выдает общее кол-во устройств в базе и кол-во собранных интерфейсов и VLAN
    """
    def get(self, request):
        status, code = auth_check(request)     # Проверка авторизации пользователя
        if status:
            return Response(status, status=code)
        data_dir = get_dat_gir()    # Получаем папку с данными
        devs_count, intf_count, vlans_count = 0, 0, 0
        try:
            all_devices = os.listdir(data_dir)  # Все папки
            devs_count = len(all_devices)
            for device in all_devices:
                if os.path.exists(f'{data_dir}/{device}/interfaces.yaml'):
                    intf_count += 1
                if os.path.exists(f'{data_dir}/{device}/vlans.yaml'):
                    vlans_count += 1
        except Exception as e:
            return Response({'error': e})
        data = {
            "all_devices": devs_count,
            "stats": {
                "devs_interfaces": intf_count,
                "devs_vlans": vlans_count
            }
        }
        return Response(data)


class GetData(APIView):
    """
    Выдаем информацию о интерфейсах и VLAN
    """
    def get(self, request, type_: str):
        status, code = auth_check(request)     # Проверка авторизации пользователя
        if status:
            return Response(status, status=code)

        if not request.GET.get('dev'):  # В запросе должно быть указано имя устройства
            return Response({'error': 'No device name'}, status=400)  # Неверный запрос
        device = request.GET['dev']

        data_dir = get_dat_gir()  # Получаем папку с данными
        if not os.path.exists(data_dir):
            return Response({'error': "Can't find data"}, status=500)  # Не найдена папка с данными
        if not os.path.exists(f"{data_dir}/{device}"):
            return Response({'error': "Device not exist"}, status=400)  # Устройство не найдено
        if not os.path.exists(f"{data_dir}/{device}/{type_}.yaml"):
            return Response({'error': f"{type_.capitalize()} not exists"}, status=400)  # Интерфейсы/vlans не найдены
        try:
            with open(f"{data_dir}/{device}/{type_}.yaml") as file:  # Открываем файл с интерфейсами/vlans
                data = yaml.safe_load(file)  # Переводим YAML в словарь
                if type_ == 'vlans':  # Если был поиск VLAN то убираем лишние символы из перечня вланов
                    for i in data['data']:
                        i["VLAN's"] = i["VLAN's"].strip().replace('\n', '').replace('\r', '')
                        i["VLAN's"] = i["VLAN's"].split(',')  # Создаем список из номеров VLAN
        except PermissionError:
            return Response({'error': "PermissionError"}, status=403)  # Нет разрешений на чтение файла
        except Exception as e:
            return Response({'error': e}, status=500)  # Другая ошибка

        if not request.GET.get('interface'):  # Если интерфейс/vlan не указан явно
            return Response(data['data'])  # Отправляем все данные
        try:
            intf_num = int(request.GET['interface'])
            if intf_num > len(data['data']) or intf_num < 1:  # Если переданный номер интерфейса выходит за пределы
                return Response({'error': "Interface number out of range"}, status=400)
        except ValueError:
            return Response({'error': "Interface parameter must be integer"}, status=400)  # Неверно передан интерфейс
        return Response(data['data'][intf_num - 1])


class GetVlan(APIView):
    """
    Выводит VLAN и его описание
    """
    def get(self, request, vid: int):
        try:
            vid = int(vid)  # Пробуем перевести переданный VLAN в число
            if 0 > vid or vid > 4096:  # Если переданный номер VLAN выходит за пределы
                return Response({'error': f"VLAN ({vid}) out of range [1; 4096]"}, status=400)
        except ValueError:  # Если не удалось перевести VLAN в число
            return Response({'error': "VLAN must be integer"}, status=400)  # Неверно передан VLAN
        except Exception as e:
            return Response({'error': e}, status=500)  # Ошибка на сервере

        if os.path.exists(f"{sys.path[0]}/vlan_traceroute/vlans.yaml"):  # Проверяем, есть ли файл соответствия
            with open(f"{sys.path[0]}/vlan_traceroute/vlans.yaml") as vfile:
                vlans = yaml.safe_load(vfile)
            return Response({'vlan': vid, 'description': vlans.get(vid) or ""})  # Выводим VLAN и его описание

        return Response({'vlan': vid, 'description': ''})  # Если не существует файла соответствия VLAN и описания


class GetVlanByDesc(APIView):
    """
    Осуществляет поиск VLAN по части его описания
    """
    def get(self, request, desc):
        if os.path.exists(f"{sys.path[0]}/vlan_traceroute/vlans.yaml"):
            with open(f"{sys.path[0]}/vlan_traceroute/vlans.yaml") as vfile:
                vlans = yaml.safe_load(vfile)
            result = []
            for k in vlans:  # Проходимся по каждому влану
                if desc.lower() in vlans[k].lower():  # Ищем совпадения в описании
                    result.append({'vlan': k, "description": vlans[k]})  # Добавляем совпадение в список
            return Response(result)
        return Response({""})
