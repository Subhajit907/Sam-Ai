"""Convert alia_avatar.jpg to a multi-size .ico file for the Windows build."""
from PIL import Image

sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img = Image.open("modules/assets/alia_avatar.jpg").convert("RGBA")
icons = [img.resize(s, Image.LANCZOS) for s in sizes]
icons[0].save(
    "modules/assets/alia_icon.ico",
    format="ICO",
    sizes=sizes,
    append_images=icons[1:],
)
print("Icon created: modules/assets/alia_icon.ico")
