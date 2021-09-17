from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from find_desc.finder import find_description, get_stat


@login_required(login_url='accounts/login/')
def home(request):
    devs_count, intf_count = get_stat()
    return render(
        request,
        'find_descr.html',
        {
            "devs_count": devs_count,
            'intf_count': intf_count or 'None'
        }
    )


@login_required(login_url='accounts/login/')
def find_as_str(request):
    print(request.GET.dict())
    if not request.GET.get('string'):
        return JsonResponse({
            'data': []
        })
    result = find_description(
        finding_string=request.GET.get('string') if request.GET.get('type') == 'string' else '',
        re_string=request.GET.get('string') if request.GET.get('type') == 'regex' else '',
        stop_on=request.GET.get('stop_on')
    )
    print(len(result))
    # print({'data': result, 'status': 'next' if result else 'end'})
    return JsonResponse({
        'data': result,
        'status': 'next' if result else 'end'
    })
