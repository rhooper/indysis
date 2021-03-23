from django.urls import reverse
from navutils import menu

main_menu = menu.registry.get("main")
if main_menu is None:
    main_menu = menu.Menu('main')
    menu.register(main_menu)

management: menu.Node = main_menu.get('management')
management.add(menu.AnyPermissionsNode(
    id='google_sync',
    label='Google Synchronization',
    pattern_name='googlesync:index',
    permissions=["googlesync.synchronize"]))

