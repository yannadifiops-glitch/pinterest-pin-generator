import io
import os
import zipfile
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

PIN_W, PIN_H = 1000, 1500


# -----------------------------
# Fonts
# -----------------------------
def font_path(kind="serif_bold"):
    fonts = {
        "serif_bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
            "C:/Windows/Fonts/georgiab.ttf",
            "C:/Windows/Fonts/georgia.ttf",
        ],
        "sans_bold": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ],
        "sans": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ],
    }

    for path in fonts.get(kind, []):
        if os.path.exists(path):
            return path

    return None


SERIF_BOLD = font_path("serif_bold")
SANS_BOLD = font_path("sans_bold")
SANS = font_path("sans")


def load_font(path, size):
    try:
        if path:
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    return ImageFont.load_default()


# -----------------------------
# Image sizing
# -----------------------------
def fit_cover(img, size=(PIN_W, PIN_H)):
    img = img.convert("RGB")
    target_w, target_h = size
    w, h = img.size

    scale = max(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)

    img = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2

    return img.crop((left, top, left + target_w, top + target_h)).convert("RGBA")


def fit_contain_with_blur(img, size=(PIN_W, PIN_H)):
    img = img.convert("RGB")
    target_w, target_h = size
    w, h = img.size

    # blurred background from same image
    bg = fit_cover(img, size).filter(Image.Filter.GaussianBlur(18)) if False else None

    bg = fit_cover(img, size)
    bg = bg.filter(ImageFilter.GaussianBlur(22))

    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)

    fg = img.resize((new_w, new_h), Image.LANCZOS).convert("RGBA")

    x = (target_w - new_w) // 2
    y = (target_h - new_h) // 2

    bg.alpha_composite(fg, (x, y))
    return bg


# Pillow needs this imported after function definition
from PIL import ImageFilter


def prepare_image(uploaded_file, fit_mode):
    img = Image.open(uploaded_file)

    if fit_mode == "No crop - blurred background":
        return fit_contain_with_blur(img)

    return fit_cover(img)


# -----------------------------
# Text helpers
# -----------------------------
def wrap_text(draw, text, font, max_width):
    words = str(text).split()
    if not words:
        return []

    lines = []
    line = ""

    for word in words:
        test_line = (line + " " + word).strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            line = test_line
        else:
            if line:
                lines.append(line)
            line = word

    if line:
        lines.append(line)

    return lines


def fit_font_to_box(draw, text, font_file, start_size, min_size, max_width, max_lines=3):
    size = start_size

    while size >= min_size:
        f = load_font(font_file, size)
        lines = wrap_text(draw, text, f, max_width)

        too_many_lines = len(lines) > max_lines
        too_wide = False

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=f)
            if bbox[2] - bbox[0] > max_width:
                too_wide = True
                break

        if not too_many_lines and not too_wide:
            return f, lines

        size -= 4

    f = load_font(font_file, min_size)
    return f, wrap_text(draw, text, f, max_width)


def draw_centered_lines(draw, lines, font, center_y, fill, spacing=10, shadow=True):
    heights = []
    total_h = 0

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        heights.append(h)
        total_h += h

    total_h += spacing * max(0, len(lines) - 1)
    y = center_y - total_h / 2

    for line, h in zip(lines, heights):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (PIN_W - w) / 2

        if shadow:
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 90))

        draw.text((x, y), line, font=font, fill=fill)
        y += h + spacing


def draw_center_text(draw, text, font_file, start_size, min_size, center_y, fill, max_width, max_lines=3, spacing=10, shadow=True):
    font, lines = fit_font_to_box(
        draw=draw,
        text=text,
        font_file=font_file,
        start_size=start_size,
        min_size=min_size,
        max_width=max_width,
        max_lines=max_lines,
    )

    draw_centered_lines(
        draw=draw,
        lines=lines,
        font=font,
        center_y=center_y,
        fill=fill,
        spacing=spacing,
        shadow=shadow,
    )


def draw_left_text(draw, text, font, x, y, fill, max_width, spacing=10):
    lines = wrap_text(draw, text, font, max_width)

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + spacing

    return y


# -----------------------------
# Templates
# -----------------------------
def template_bottom_banner(img, title, subtitle):
    draw = ImageDraw.Draw(img, "RGBA")

    banner_h = 410
    banner_y = PIN_H - banner_h

    # warm brown banner
    draw.rectangle((0, banner_y, PIN_W, PIN_H), fill=(120, 82, 52, 238))

    draw_center_text(
        draw,
        title.upper(),
        SANS_BOLD,
        start_size=86,
        min_size=46,
        center_y=banner_y + 150,
        fill=(255, 246, 230, 255),
        max_width=850,
        max_lines=2,
        spacing=8,
        shadow=True,
    )

    sub_font = load_font(SANS, 34)
    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    sub_w = bbox[2] - bbox[0]

    draw.text(
        ((PIN_W - sub_w) / 2, banner_y + 300),
        subtitle,
        font=sub_font,
        fill=(255, 246, 230, 255),
    )

    return img


def template_gradient_overlay(img, title, subtitle):
    overlay = Image.new("RGBA", (PIN_W, PIN_H), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    for y in range(PIN_H):
        if y > PIN_H * 0.48:
            alpha = int(((y - PIN_H * 0.48) / (PIN_H * 0.52)) * 215)
            overlay_draw.line((0, y, PIN_W, y), fill=(50, 31, 18, min(alpha, 215)))

    img.alpha_composite(overlay)
    draw = ImageDraw.Draw(img, "RGBA")

    draw_center_text(
        draw,
        title,
        SERIF_BOLD,
        start_size=90,
        min_size=46,
        center_y=PIN_H - 305,
        fill=(255, 246, 230, 255),
        max_width=850,
        max_lines=3,
        spacing=8,
        shadow=True,
    )

    sub_font = load_font(SANS, 34)
    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    sub_w = bbox[2] - bbox[0]

    draw.text(
        ((PIN_W - sub_w) / 2, PIN_H - 150),
        subtitle,
        font=sub_font,
        fill=(255, 246, 230, 255),
    )

    return img


def template_simple_top_overlay(img, title, subtitle):
    draw = ImageDraw.Draw(img, "RGBA")

    box = (80, 95, 920, 380)
    draw.rounded_rectangle(box, radius=35, fill=(255, 247, 232, 215))
    draw.rounded_rectangle(box, radius=35, outline=(255, 255, 255, 150), width=3)

    draw_center_text(
        draw,
        title,
        SERIF_BOLD,
        start_size=82,
        min_size=42,
        center_y=205,
        fill=(68, 43, 27, 255),
        max_width=760,
        max_lines=2,
        spacing=6,
        shadow=False,
    )

    sub_font = load_font(SANS, 32)
    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    sub_w = bbox[2] - bbox[0]

    draw.text(
        ((PIN_W - sub_w) / 2, 300),
        subtitle,
        font=sub_font,
        fill=(68, 43, 27, 255),
    )

    return img


def template_split_panel(img, title, subtitle):
    photo_h = 870

    photo = img.crop((0, 0, PIN_W, photo_h))
    canvas = Image.new("RGBA", (PIN_W, PIN_H), (247, 241, 229, 255))
    canvas.alpha_composite(photo, (0, 0))

    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rectangle((0, photo_h, PIN_W, PIN_H), fill=(247, 241, 229, 255))

    title_font = load_font(SERIF_BOLD, 78)
    x = 105
    y = photo_h + 105

    y = draw_left_text(
        draw,
        title,
        title_font,
        x,
        y,
        (63, 42, 29, 255),
        max_width=790,
        spacing=8,
    )

    draw.line((x, y + 22, x + 230, y + 22), fill=(164, 111, 70, 255), width=5)

    sub_font = load_font(SANS, 36)
    draw_left_text(
        draw,
        subtitle,
        sub_font,
        x,
        y + 65,
        (75, 55, 42, 255),
        max_width=790,
        spacing=8,
    )

    return canvas


def template_recipe_card(img, title, subtitle):
    canvas = Image.new("RGBA", (PIN_W, PIN_H), (245, 237, 220, 255))
    draw = ImageDraw.Draw(canvas, "RGBA")

    # Border
    draw.rounded_rectangle((45, 45, PIN_W - 45, PIN_H - 45), radius=25, outline=(140, 100, 65, 150), width=4)
    draw.rounded_rectangle((75, 75, PIN_W - 75, PIN_H - 75), radius=20, outline=(140, 100, 65, 75), width=2)

    # Photo inset
    photo_box = (110, 115, 890, 850)
    photo_w = photo_box[2] - photo_box[0]
    photo_h = photo_box[3] - photo_box[1]

    photo = img.resize((PIN_W, PIN_H), Image.LANCZOS)
    photo = fit_cover(photo, (photo_w, photo_h))

    mask = Image.new("L", (photo_w, photo_h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, photo_w, photo_h), radius=28, fill=255)

    canvas.paste(photo, (photo_box[0], photo_box[1]), mask)
    draw.rounded_rectangle(photo_box, radius=28, outline=(255, 255, 255, 210), width=6)

    draw_center_text(
        draw,
        title,
        SERIF_BOLD,
        start_size=90,
        min_size=48,
        center_y=1050,
        fill=(63, 42, 29, 255),
        max_width=820,
        max_lines=2,
        spacing=5,
        shadow=False,
    )

    draw.line((250, 1225, 750, 1225), fill=(140, 100, 65, 150), width=3)

    sub_font = load_font(SANS, 36)
    bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    sub_w = bbox[2] - bbox[0]

    draw.text(
        ((PIN_W - sub_w) / 2, 1270),
        subtitle,
        font=sub_font,
        fill=(88, 65, 48, 255),
    )

    return canvas


def create_pin(uploaded_file, title, subtitle, template_name, fit_mode):
    img = prepare_image(uploaded_file, fit_mode)

    if template_name == "Bottom Banner":
        img = template_bottom_banner(img, title, subtitle)
    elif template_name == "Gradient Overlay":
        img = template_gradient_overlay(img, title, subtitle)
    elif template_name == "Simple Top Overlay":
        img = template_simple_top_overlay(img, title, subtitle)
    elif template_name == "Split Panel":
        img = template_split_panel(img, title, subtitle)
    elif template_name == "Recipe Card":
        img = template_recipe_card(img, title, subtitle)

    output = io.BytesIO()
    img.convert("RGB").save(output, format="JPEG", quality=95, optimize=True)
    output.seek(0)

    return output, img.convert("RGB")


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(
    page_title="Pinterest Pin Generator",
    page_icon="📌",
    layout="wide",
)

st.title("📌 Pinterest Pin Generator")
st.write("Upload your images, choose a template, add overlay text, and export ready Pinterest pins.")

with st.sidebar:
    st.header("Pin Settings")

    template_name = st.selectbox(
        "Choose Template",
        [
            "Bottom Banner",
            "Gradient Overlay",
            "Simple Top Overlay",
            "Split Panel",
            "Recipe Card",
        ],
    )

    fit_mode = st.selectbox(
        "Image Fit Mode",
        [
            "Cover crop",
            "No crop - blurred background",
        ],
    )

    title = st.text_input("Overlay Title", "Homemade Flatbread")
    subtitle = st.text_input("Overlay Subtitle", "Soft · Easy · Skillet Bread")

uploaded_images = st.file_uploader(
    "Upload images",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
)

generate = st.button("Generate Pins", type="primary")

if generate:
    if not uploaded_images:
        st.warning("Please upload at least one image.")
    else:
        zip_buffer = io.BytesIO()

        st.subheader("Preview")
        cols = st.columns(3)

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for index, uploaded_file in enumerate(uploaded_images):
                output, preview_img = create_pin(
                    uploaded_file=uploaded_file,
                    title=title,
                    subtitle=subtitle,
                    template_name=template_name,
                    fit_mode=fit_mode,
                )

                clean_name = uploaded_file.name.rsplit(".", 1)[0]
                filename = f"{clean_name}_pin.jpg"

                zip_file.writestr(filename, output.getvalue())

                with cols[index % 3]:
                    st.image(preview_img, caption=filename, use_container_width=True)

        zip_buffer.seek(0)

        st.download_button(
            label="Download ZIP",
            data=zip_buffer,
            file_name="pinterest_pins.zip",
            mime="application/zip",
        )
