from imgui_bundle import imgui
from app import App

app = App()
while app.run_frame():
	if imgui.begin_main_menu_bar():
		if imgui.begin_menu("File", True):
			clicked_new, selected_new = imgui.menu_item("New", None, None)
			clicked_exit, selected_exit = imgui.menu_item("Exit", None, None)
			if clicked_exit:
				app.close_next_update()
			imgui.end_menu()
		imgui.end_main_menu_bar()

	imgui.dock_space_over_viewport()

	imgui.show_demo_window()

	imgui.begin("Test")
	imgui.text("Hello, world!")
	imgui.end()

	app.render()

app.shutdown()
