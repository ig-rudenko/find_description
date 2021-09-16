from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from find_desc.finder import find_description


@login_required(login_url='accounts/login/')
def home(request):
    return render(
        request,
        'find_descr.html'
    )


@login_required(login_url='accounts/login/')
def find_as_str(request):
    print(request.GET.dict())
    if not request.GET.get('string'):
        return JsonResponse({
            'data': []
        })
    result = find_description(
        find_str=[request.GET.get('string')] if request.GET.get('type') == 'string' else [],
        find_re=[request.GET.get('string')] if request.GET.get('type') == 'regex' else [],
        stop_on=request.GET.get('stop_on')
    )
    print({
        'data': result,
        'status': 'next' if result else 'end'
    })
    return JsonResponse({
        'data': result,
        'status': 'next' if result else 'end'
    })
