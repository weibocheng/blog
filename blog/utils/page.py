from django.core.paginator import Paginator, EmptyPage


def page(foo, request, per_page_number):
    """
    :param foo: 要进行分页的对象
    :param request: request
    :param per_page_number: 每页显示的个数
    :return:
    """
    paginator = Paginator(foo, per_page_number)

    current_page_num = int(request.GET.get("page", 1))

    if paginator.num_pages > 11:

        if current_page_num - 5 < 1:
            page_range = range(1, 12)
        elif current_page_num + 5 > paginator.num_pages:
            page_range = range(paginator.num_pages - 10, paginator.num_pages + 1)
        else:
            page_range = range(current_page_num - 5, current_page_num + 6)
    else:
        page_range = paginator.page_range
    try:
        current_page = paginator.page(current_page_num)
    except EmptyPage:
        current_page = paginator.page(1)

    return page_range, current_page
