from django.urls import reverse
from navutils import menu

main_menu = menu.registry.get("main")
if main_menu is None:
    main_menu = menu.Menu('main')
    menu.register(main_menu)

management: menu.Node = main_menu.get('management')
management.add(menu.AnyPermissionsNode(
    id='broadcast',
    label='Emergency Broadcast',
    pattern_name='broadcast:index',
    permissions=["broadcast.send"]))

