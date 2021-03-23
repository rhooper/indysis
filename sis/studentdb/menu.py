from navutils import menu

main_menu = menu.registry.get("main")
if main_menu is None:
    main_menu = menu.Menu('main')
    menu.register(main_menu)

# TODO - Implement Database menus
# home = menu.Node(id='home', label='Home', url="/")
# main_menu.register(home)

management = main_menu.get('management')
if management is None:
    management = menu.AnyPermissionsNode(
        id='management',
        label='Management',
        url='/administration/dashboard/',
        permissions=["auth.change_user", "administration.change_configuration"])
    main_menu.register(management)

management.add(menu.AnyPermissionsNode(
    id='management_dashboard',
    label='Dashboard',
    url='/administration/dashboard/',
    permissions=["auth.change_user", "administration.change_configuration"]))
management.add(menu.AnyPermissionsNode(
    id='management_config',
    label='Configuration',
    url='/admin/constance/config',
    permissions=["administration.change_constance"]))

