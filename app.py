from imgui_bundle import imgui
from imgui_bundle.python_backends.glfw_backend import GlfwRenderer
import glfw
import OpenGL.GL as gl

class App:
	def __init__(self, name : str = "window", dimensions : tuple[int, int] = (800, 600)):
		imgui.create_context()
		# Initialize the GLFW window
		if not glfw.init():
			raise RuntimeError("Could not initialize OpenGL context")
		# OS X supports only forward-compatible core profiles from 3.2
		glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
		glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
		glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
		glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)
		# Create a windowed mode window and its OpenGL context
		self.window = glfw.create_window(dimensions[0], dimensions[1], name, None, None)
		glfw.make_context_current(self.window)
		if not self.window:
			glfw.terminate()
			raise RuntimeError("Could not initialize Window")
		self.renderer = GlfwRenderer(self.window)
		# Note:
		# The way font are loaded in this example is a bit tricky.
		# We are not using imgui.backends.opengl3_XXX anywhere else, because the rendering is done via Python.
		#
		# Howver, we will here need to:
		#     - call imgui.backends.opengl3_init(glsl_version) at startup
		#     - call imgui.backends.opengl3_new_frame() after loading the fonts, because this is how ImGui
		#       will load the fonts into a texture (using imgui.get_io().fonts.build() is not enough)
		# We need to initialize the OpenGL backend (so that we can later call opengl3_new_frame)
		imgui.backends.opengl3_init("#version 100")
		imgui.get_io().fonts.clear()
		imgui.get_io().fonts.add_font_default()
		# Load markdown fonts
		# imgui_md.initialize_markdown()
		# font_loader = imgui_md.get_font_loader_function()
		# font_loader()
		# We need to call this function to load the fonts into a texture
		imgui.backends.opengl3_new_frame()
		imgui.get_io().display_size = (800, 600)
		imgui.get_io().config_flags |= imgui.ConfigFlags_.docking_enable

	def run_frame(self) -> bool:
		if (glfw.window_should_close(self.window)):
			return False
		glfw.poll_events()
		self.renderer.process_inputs()
		imgui.new_frame()
		return True

	def render(self, clear_color : tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0), clear_mask : int = gl.GL_COLOR_BUFFER_BIT):
		imgui.end_frame()
		imgui.render()
		gl.glClearColor(clear_color[0], clear_color[1], clear_color[2], clear_color[3])
		gl.glClear(clear_mask)
		self.renderer.render(imgui.get_draw_data())
		glfw.swap_buffers(self.window)

	def close_next_update(self):
		glfw.set_window_should_close(self.window, True)

	def shutdown(self):
		self.renderer.shutdown()
		glfw.destroy_window(self.window)
		glfw.terminate()
