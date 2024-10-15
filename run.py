from imgui_bundle import imgui, imgui_ctx
from app import App

app = App()
while app.run_frame():

	with imgui_ctx.begin_main_menu_bar():
		with imgui_ctx.begin_menu("File", True) as file_menu:
			if file_menu:
				clicked_new, selected_new = imgui.menu_item("New", None, None)
				clicked_exit, selected_exit = imgui.menu_item("Exit", None, None)
				if clicked_exit:
					app.close_next_update()

	imgui.dock_space_over_viewport()

	imgui.show_demo_window()

	with imgui_ctx.begin("Test"):
		imgui.text("Hello, world!")

	app.render()

app.shutdown()
